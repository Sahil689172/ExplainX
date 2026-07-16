"""Tests for Renderer Phase 3 — Scene Composer."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.features.projects.filesystem import ProjectFilesystem
from app.features.renderer.scene import scene_frame_count, total_frame_count
from app.features.renderer.scene_manifest import (
    load_scene_manifest,
    manifest_exists,
    ordered_scenes,
    resolve_scene_image,
)
from app.features.renderer.scene_schemas import (
    SceneCameraSettings,
    SceneDefinition,
    SceneManifest,
    SceneMetadata,
)
from app.features.renderer.scene_service import SceneComposer
from app.features.renderer.service import RenderService
from app.features.renderer.schemas import RenderConfig

_MINIMAL_PNG = bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

PROJECT_ID = "11111111-1111-1111-1111-111111111111"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_root=str(tmp_path),
        env="testing",
        render_fps=15,
        default_duration_seconds=60,
        frame_output_format="png",
        ffmpeg_executable="ffmpeg",
    )


def _write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_MINIMAL_PNG)


def _sample_manifest(*, durations: tuple[int, ...] = (8, 10, 12)) -> dict:
    scenes = []
    for i, duration in enumerate(durations, start=1):
        scenes.append(
            {
                "scene_id": f"scene_{i:02d}",
                "image": f"assets/scene_{i:02d}.png",
                "duration": duration,
                "camera": "zoom_in" if i == 1 else "center",
                "camera_settings": {
                    "start_scale": 1.0,
                    "end_scale": 1.15,
                    "easing": "ease_in_out",
                },
            }
        )
    return {
        "video_duration": sum(durations),
        "fps": 15,
        "scenes": scenes,
    }


def _seed_manifest_project(tmp_path: Path) -> Path:
    fs = ProjectFilesystem(_settings(tmp_path))
    root = fs.project_root(PROJECT_ID)
    for i in (1, 2, 3):
        _write_image(root / "assets" / f"scene_{i:02d}.png")
    manifest = _sample_manifest()
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "scene_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return root


def test_manifest_exists(tmp_path: Path) -> None:
    root = _seed_manifest_project(tmp_path)
    assert manifest_exists(root) is True
    assert manifest_exists(root / "missing") is False


def test_load_scene_manifest_ordering(tmp_path: Path) -> None:
    root = _seed_manifest_project(tmp_path)
    manifest = load_scene_manifest(root)
    scenes = ordered_scenes(manifest)
    assert [s.scene_id for s in scenes] == ["scene_01", "scene_02", "scene_03"]
    assert scenes[0].duration == 8
    assert scenes[1].camera.value == "center"


def test_scene_frame_counting() -> None:
    scenes = [
        SceneDefinition(
            scene_id="a",
            image="x.png",
            duration=8,
            camera="center",
        ),
        SceneDefinition(
            scene_id="b",
            image="y.png",
            duration=10,
            camera="zoom_in",
        ),
    ]
    assert scene_frame_count(duration_sec=8, fps=15) == 120
    assert total_frame_count(scenes, fps=15) == 270


def test_manifest_rejects_missing_image(tmp_path: Path) -> None:
    root = _seed_manifest_project(tmp_path)
    manifest_path = root / "artifacts" / "scene_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["scenes"][1]["image"] = "assets/missing.png"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationAppError) as exc:
        load_scene_manifest(root)
    assert exc.value.code == "SCENE_IMAGE_NOT_FOUND"


def test_manifest_rejects_duration_mismatch(tmp_path: Path) -> None:
    root = _seed_manifest_project(tmp_path)
    manifest_path = root / "artifacts" / "scene_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["video_duration"] = 999
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationAppError) as exc:
        load_scene_manifest(root)
    assert exc.value.code == "SCENE_MANIFEST_INVALID"


def test_scene_compose_frame_indices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _seed_manifest_project(tmp_path)
    settings = _settings(tmp_path)
    fs = ProjectFilesystem(settings)
    from app.features.renderer.artifacts import RenderArtifactStore

    store = RenderArtifactStore(fs)
    config = RenderConfig(fps=15, duration_sec=30, frame_format="png")
    calls: list[int] = []

    def fake_segment(**kwargs):  # noqa: ANN003
        calls.append(kwargs["frame_start_index"])
        return kwargs["fps"] * kwargs["duration_sec"]

    monkeypatch.setattr(
        "app.features.renderer.scene_service.generate_camera_frames_segment",
        fake_segment,
    )
    composer = SceneComposer(settings=settings, store=store)
    result = composer.compose(PROJECT_ID, root, base_config=config)
    assert calls == [1, 121, 271]
    assert result.total_frames == 450
    assert result.metadata.scene_count == 3
    assert result.metadata.frames_per_scene == [120, 150, 180]


def test_scene_metadata_shape() -> None:
    meta = SceneMetadata(
        scene_count=2,
        scene_duration=[8, 10],
        frames_per_scene=[120, 150],
        camera_used=["Zoom In", "Center"],
        total_frames=270,
        fps=15,
        video_duration=18,
        scenes=[],
    )
    data = json.loads(meta.model_dump_json())
    assert data["scene_count"] == 2
    assert data["frames_per_scene"] == [120, 150]


def test_render_fallback_single_scene(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)
    fs = ProjectFilesystem(settings)
    root = fs.project_root(PROJECT_ID)
    _write_image(root / "assets" / "plant.png")

    called = {"single": False, "multi": False}

    def fake_single(self, project_id, project_root, config):  # noqa: ANN001
        called["single"] = True
        from app.features.renderer.schemas import RenderMetadata

        return SimpleNamespace(
            project_id=project_id,
            input_image=project_root / "assets" / "plant.png",
            video_path=root / "artifacts" / "video.mp4",
            metadata_path=root / "artifacts" / "render_metadata.json",
            metadata=RenderMetadata(
                fps=15,
                duration=60,
                frame_count=1,
                resolution="1x1",
                render_time=0.1,
                input_image="plant.png",
            ),
            camera_metadata_path=root / "artifacts" / "camera_metadata.json",
            scene_metadata_path=None,
            multi_scene=False,
        )

    def fake_multi(self, project_id, project_root, config):  # noqa: ANN001
        called["multi"] = True
        raise AssertionError("should not run")

    monkeypatch.setattr(RenderService, "_render_single", fake_single)
    monkeypatch.setattr(RenderService, "_render_scenes", fake_multi)

    service = RenderService(MagicMock(), settings)
    service._repo.get = MagicMock(return_value=object())  # type: ignore[method-assign]
    result = service.render(PROJECT_ID)
    assert called["single"] is True
    assert called["multi"] is False
    assert result.multi_scene is False


def test_render_uses_scenes_when_manifest_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _seed_manifest_project(tmp_path)
    settings = _settings(tmp_path)

    called = {"single": False, "multi": False}

    def fake_single(self, project_id, project_root, config):  # noqa: ANN001
        called["single"] = True
        raise AssertionError("should not run")

    def fake_multi(self, project_id, project_root, config):  # noqa: ANN001
        called["multi"] = True
        from app.features.renderer.schemas import RenderMetadata

        return SimpleNamespace(
            project_id=project_id,
            input_image=resolve_scene_image(project_root, "assets/scene_01.png"),
            video_path=project_root / "artifacts" / "video.mp4",
            metadata_path=project_root / "artifacts" / "render_metadata.json",
            metadata=RenderMetadata(
                fps=15,
                duration=30,
                frame_count=450,
                resolution="1x1",
                render_time=0.1,
                input_image="scene_01.png",
            ),
            camera_metadata_path=None,
            scene_metadata_path=project_root / "artifacts" / "scene_metadata.json",
            multi_scene=True,
        )

    monkeypatch.setattr(RenderService, "_render_single", fake_single)
    monkeypatch.setattr(RenderService, "_render_scenes", fake_multi)

    service = RenderService(MagicMock(), settings)
    service._repo.get = MagicMock(return_value=object())  # type: ignore[method-assign]
    result = service.render(PROJECT_ID)
    assert called["multi"] is True
    assert called["single"] is False
    assert result.multi_scene is True


def test_scene_to_camera_config() -> None:
    scene = SceneDefinition(
        scene_id="scene_01",
        image="assets/a.png",
        duration=8,
        camera="zoom_in",
        camera_settings=SceneCameraSettings(
            start_scale=1.0,
            end_scale=1.2,
            easing="ease_out",
        ),
    )
    cfg = scene.to_camera_config()
    assert cfg.duration == 8
    assert cfg.end_scale == 1.2
    assert cfg.easing == "ease_out"
