"""Tests for Renderer MVP (static image → frames → video.mp4)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.errors import ExplainXError, NotFoundError
from app.features.projects.filesystem import ProjectFilesystem
from app.features.renderer.artifacts import RenderArtifactStore
from app.features.renderer.exporter import export_video, resolve_ffmpeg_executable
from app.features.renderer.frame_renderer import (
    discover_input_image,
    generate_identical_frames,
    read_image_resolution,
)
from app.features.renderer.schemas import RenderConfig, RenderMetadata
from app.features.renderer.service import RenderService

# Minimal valid 1×1 PNG (red pixel).
_MINIMAL_PNG = bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base = {
        "data_root": str(tmp_path),
        "env": "testing",
        "ollama_enabled": False,
        "render_fps": 3,
        "default_duration_seconds": 2,
        "frame_output_format": "png",
        "ffmpeg_executable": "ffmpeg",
    }
    base.update(overrides)
    return Settings(**base)


def _seed_project_image(tmp_path: Path, project_id: str, name: str = "plant.png") -> Path:
    fs = ProjectFilesystem(_settings(tmp_path))
    root = fs.project_root(project_id)
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    image = assets / name
    image.write_bytes(_MINIMAL_PNG)
    return image


def test_read_png_resolution(tmp_path: Path) -> None:
    image = tmp_path / "test.png"
    image.write_bytes(_MINIMAL_PNG)
    assert read_image_resolution(image) == (1, 1)


def test_even_dimensions() -> None:
    from app.features.renderer.frame_renderer import even_dimensions

    assert even_dimensions(491, 351) == (490, 350)
    assert even_dimensions(1920, 1080) == (1920, 1080)
    assert even_dimensions(1, 1) == (2, 2)


def test_discover_input_image_prefers_assets(tmp_path: Path) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    image = _seed_project_image(tmp_path, project_id, "plant.png")
    fs = ProjectFilesystem(_settings(tmp_path))
    found = discover_input_image(fs.project_root(project_id))
    assert found == image


def test_discover_input_image_missing_raises(tmp_path: Path) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    fs = ProjectFilesystem(_settings(tmp_path))
    root = fs.project_root(project_id)
    root.mkdir(parents=True)
    with pytest.raises(NotFoundError) as exc:
        discover_input_image(root)
    assert exc.value.code == "RENDER_INPUT_IMAGE_NOT_FOUND"


def test_generate_identical_frames(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(_MINIMAL_PNG)
    frames_dir = tmp_path / "frames"
    config = RenderConfig(fps=3, duration_sec=2, frame_format="png")
    count = generate_identical_frames(
        source_image=source,
        frames_dir=frames_dir,
        config=config,
    )
    assert count == 6
    assert (frames_dir / "000001.png").is_file()
    assert (frames_dir / "000006.png").is_file()
    assert (frames_dir / "000001.png").read_bytes() == _MINIMAL_PNG


def test_render_metadata_roundtrip() -> None:
    meta = RenderMetadata(
        fps=15,
        duration=60,
        frame_count=900,
        resolution="1280x720",
        render_time=3.4,
        input_image="plant.png",
    )
    data = json.loads(meta.model_dump_json())
    assert data["frame_count"] == 900
    assert data["resolution"] == "1280x720"


def test_export_video_invokes_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "000001.png").write_bytes(_MINIMAL_PNG)
    output = tmp_path / "video.mp4"
    config = RenderConfig(fps=3, duration_sec=1, frame_format="png")

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        output.write_bytes(b"FAKE_MP4")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr("app.features.renderer.exporter.subprocess.run", fake_run)
    path = export_video(
        frames_dir=frames_dir,
        output_video=output,
        config=config,
        ffmpeg_executable="ffmpeg",
    )
    assert path == output
    assert output.is_file()


def test_export_video_failure_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "000001.png").write_bytes(_MINIMAL_PNG)
    output = tmp_path / "video.mp4"
    config = RenderConfig(fps=3, duration_sec=1, frame_format="png")

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        return SimpleNamespace(returncode=1, stderr=b"boom")

    monkeypatch.setattr("app.features.renderer.exporter.subprocess.run", fake_run)
    with pytest.raises(ExplainXError) as exc:
        export_video(
            frames_dir=frames_dir,
            output_video=output,
            config=config,
            ffmpeg_executable="ffmpeg",
        )
    assert exc.value.code == "FFMPEG_EXPORT_FAILED"


def test_render_service_creates_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    settings = _settings(tmp_path)
    _seed_project_image(tmp_path, project_id)

    def fake_export(**kwargs):  # noqa: ANN003
        out = kwargs["output_video"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"FAKE_MP4")
        return out

    def fake_generate_camera_frames(**kwargs):  # noqa: ANN003
        frames_dir = kwargs["frames_dir"]
        config = kwargs["config"]
        ext = config.frame_format
        frames_dir.mkdir(parents=True, exist_ok=True)
        for index in range(1, config.frame_count + 1):
            (frames_dir / f"{index:06d}.{ext}").write_bytes(_MINIMAL_PNG)
        return config.frame_count

    monkeypatch.setattr(
        "app.features.renderer.service.export_video",
        fake_export,
    )
    monkeypatch.setattr(
        "app.features.renderer.service.generate_camera_frames",
        fake_generate_camera_frames,
    )
    monkeypatch.setattr(
        "app.features.renderer.service.resolve_ffmpeg_executable",
        lambda *_a, **_k: "ffmpeg",
    )

    service = RenderService(MagicMock(), settings)
    service._repo.get = MagicMock(return_value=object())  # type: ignore[method-assign]

    result = service.render(project_id)
    store = RenderArtifactStore(ProjectFilesystem(settings))

    assert result.video_path.is_file()
    assert store.metadata_path(project_id).is_file()
    assert store.camera_metadata_path(project_id).is_file()
    assert store.frames_dir(project_id).is_dir()
    assert len(list(store.frames_dir(project_id).glob("*.png"))) == 6

    meta = json.loads(store.metadata_path(project_id).read_text(encoding="utf-8"))
    assert meta["frame_count"] == 6
    camera_meta = json.loads(
        store.camera_metadata_path(project_id).read_text(encoding="utf-8")
    )
    assert camera_meta["camera_type"] == "center"
    assert camera_meta["zoom"] == 1.0


def test_render_artifact_paths(tmp_path: Path) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    store = RenderArtifactStore(ProjectFilesystem(_settings(tmp_path)))
    assert store.video_path(project_id).name == "video.mp4"
    assert store.metadata_path(project_id).name == "render_metadata.json"
    assert store.camera_metadata_path(project_id).name == "camera_metadata.json"
    assert store.frame_path(project_id, 1, ext="png").name == "000001.png"


def test_resolve_ffmpeg_from_path(tmp_path: Path) -> None:
    exe = tmp_path / "ffmpeg.exe"
    exe.write_bytes(b"stub")
    resolved = resolve_ffmpeg_executable(str(exe), repo_root=tmp_path)
    assert resolved == str(exe.resolve())
