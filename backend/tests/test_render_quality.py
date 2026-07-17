"""Tests for Renderer Phase 4.5 — Render Quality & Asset Normalization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.features.projects.filesystem import ProjectFilesystem
from app.features.renderer.artifacts import RenderArtifactStore
from app.features.renderer.asset_quality import (
    detect_transparency,
    inspect_asset,
    resolve_display_scale,
)
from app.features.renderer.camera_schemas import Viewport
from app.features.renderer.camera_service import CameraService
from app.features.renderer.frame_renderer import (
    even_dimensions,
    read_image_resolution,
    render_frame,
)
from app.features.renderer.layers.layer_manager import LayerManager
from app.features.renderer.scene_manifest import resolve_layer_image
from app.features.renderer.scene_schemas import (
    SceneDefinition,
    SceneObjectDefinition,
)
from app.features.renderer.scene_service import SceneComposer
from app.features.renderer.schemas import RenderConfig

pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

PROJECT_ID = "33333333-3333-3333-3333-333333333333"


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base = {
        "data_root": str(tmp_path),
        "env": "testing",
        "render_fps": 15,
        "default_duration_seconds": 2,
        "frame_output_format": "png",
        "ffmpeg_executable": "ffmpeg",
        "default_zoom": 1.15,
        "output_width": 1280,
        "output_height": 720,
    }
    base.update(overrides)
    return Settings(**base)


def _write_rgba(path: Path, *, size: tuple[int, int], color: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, color).save(path)


def _write_opaque_rgb(path: Path, *, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def test_transparent_png_detected(tmp_path: Path) -> None:
    path = tmp_path / "earth.png"
    _write_rgba(path, size=(64, 64), color=(0, 120, 255, 128))
    assert detect_transparency(path) is True
    info = inspect_asset(path, role="object")
    assert info.has_alpha is True
    assert info.warnings == []


def test_opaque_png_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "earth.png"
    _write_opaque_rgb(path, size=(64, 64), color=(0, 120, 255))
    info = inspect_asset(path, role="object")
    assert info.has_alpha is False
    assert any("no transparency" in w for w in info.warnings)
    out = capsys.readouterr().out
    assert "[Asset Warning]" in out
    assert "earth.png has no transparency." in out


def test_logical_sizing_from_display_width() -> None:
    scale = resolve_display_scale(image_width=640, display_width=120)
    assert scale == pytest.approx(0.1875)
    # Aspect preserved: uniform scale only.
    display_h = int(round(640 * scale))
    assert display_h == 120


def test_legacy_scale_fallback() -> None:
    scale = resolve_display_scale(image_width=640, scale=0.5)
    assert scale == 0.5


def test_display_width_used_in_layer_compose(tmp_path: Path) -> None:
    fs = ProjectFilesystem(_settings(tmp_path))
    root = fs.project_root(PROJECT_ID)
    _write_rgba(root / "assets" / "space.png", size=(400, 300), color=(0, 0, 40, 255))
    _write_rgba(root / "assets" / "earth.png", size=(200, 200), color=(0, 120, 255, 255))

    scene = SceneDefinition(
        scene_id="s1",
        background="assets/space.png",
        duration=1,
        objects=[
            SceneObjectDefinition(
                id="earth",
                image="assets/earth.png",
                x=200,
                y=150,
                display_width=100,
                z_index=1,
            )
        ],
    )
    manager = LayerManager()
    canvas = manager.compose_scene(root, scene, resolve_image=resolve_layer_image)
    assert canvas.size == (400, 300)
    earth = manager.last_asset_infos[-1]
    assert earth.display_width == 100
    assert earth.scale == pytest.approx(0.5)
    assert earth.display_size == (100, 100)


def test_fixed_output_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, output_width=1280, output_height=720)
    fs = ProjectFilesystem(settings)
    root = fs.project_root(PROJECT_ID)
    _write_rgba(root / "assets" / "space.png", size=(400, 300), color=(0, 0, 40, 255))
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "scene_manifest.json").write_text(
        json.dumps(
            {
                "fps": 5,
                "scenes": [
                    {
                        "scene_id": "scene1",
                        "background": "assets/space.png",
                        "duration": 1,
                        "camera": "center",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    sizes: list[tuple[int, int]] = []

    def fake_segment(**kwargs):  # noqa: ANN003
        sizes.append(kwargs["output_size"])
        # Write one real frame at the fixed output size.
        dest = kwargs["frames_dir"] / "000001.png"
        Image.new("RGB", kwargs["output_size"], (10, 10, 10)).save(dest)
        return kwargs["fps"] * kwargs["duration_sec"]

    monkeypatch.setattr(
        "app.features.renderer.scene_service.generate_camera_frames_segment",
        fake_segment,
    )
    composer = SceneComposer(
        settings=settings, store=RenderArtifactStore(fs)
    )
    result = composer.compose(
        PROJECT_ID, root, base_config=RenderConfig(fps=5, duration_sec=1, frame_format="png")
    )
    assert result.output_size == (1280, 720)
    assert sizes == [(1280, 720)]
    assert result.diagnostics.output_resolution == "1280x720"


def test_camera_smoothness_monotonic_zoom() -> None:
    from app.features.renderer.camera_schemas import CameraConfig

    camera = CameraService.from_config(
        config=CameraConfig(
            type="zoom_in",
            start_scale=1.0,
            end_scale=1.2,
            duration=2,
            easing="linear",
        ),
        image_width=800,
        image_height=600,
    )
    widths = [camera.get_viewport(t / 30).width for t in range(61)]
    # Smooth zoom-in: viewport width steadily shrinks (or stays equal).
    for prev, cur in zip(widths, widths[1:]):
        assert cur <= prev + 1e-9


def test_viewport_precision_float_until_crop(tmp_path: Path) -> None:
    source = tmp_path / "scene.png"
    _write_opaque_rgb(source, size=(200, 100), color=(20, 20, 20))
    dest = tmp_path / "frame.png"
    # Non-integer viewport from camera math.
    viewport = Viewport(x=10.4, y=5.6, width=80.8, height=40.4)
    render_frame(
        source_image=source,
        viewport=viewport,
        output_size=(1280, 720),
        dest=dest,
    )
    with Image.open(dest) as frame:
        assert frame.size == (1280, 720)


def test_crop_always_from_original_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Camera frames must reopen the composed source — never a prior frame."""
    source = tmp_path / "composed.png"
    _write_opaque_rgb(source, size=(100, 100), color=(1, 2, 3))
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    opened: list[str] = []
    real_open = Image.open

    def tracking_open(path, *args, **kwargs):  # noqa: ANN001, ANN003
        opened.append(str(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("PIL.Image.open", tracking_open)

    from app.features.renderer.camera_schemas import CameraConfig

    camera = CameraService.from_config(
        config=CameraConfig(type="zoom_in", start_scale=1.0, end_scale=1.1, duration=1),
        image_width=100,
        image_height=100,
    )
    from app.features.renderer.frame_renderer import generate_camera_frames_segment

    generate_camera_frames_segment(
        source_image=source,
        frames_dir=frames_dir,
        fps=3,
        duration_sec=1,
        frame_format="png",
        camera=camera,
        output_size=(64, 64),
        frame_start_index=1,
    )
    assert all(p.endswith("composed.png") for p in opened)
    assert len(opened) == 3


def test_legacy_scale_still_works_in_schema() -> None:
    obj = SceneObjectDefinition(id="a", image="a.png", scale=0.25)
    assert obj.display_width is None
    assert obj.scale == 0.25
    assert resolve_display_scale(image_width=400, scale=obj.scale) == 0.25


def test_even_output_dimensions() -> None:
    assert even_dimensions(1280, 720) == (1280, 720)
    assert even_dimensions(1279, 719) == (1278, 718)
