"""Tests for Renderer Phase 2 — Camera Engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.features.projects.filesystem import ProjectFilesystem
from app.features.renderer.camera import lerp, validate_viewport, viewport_for_scale
from app.features.renderer.camera_schemas import CameraConfig, CameraType, Viewport
from app.features.renderer.camera_service import CameraService, default_camera_config
from app.features.renderer.easing import apply_easing, ease_in_out, linear

def _minimal_png(*, size: tuple[int, int] = (2, 2)) -> bytes:
    """Return a Pillow-valid solid RGB PNG (even size by default for libx264)."""
    pytest.importorskip("PIL")
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", size, (200, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base = {
        "data_root": str(tmp_path),
        "env": "testing",
        "default_camera": "center",
        "default_easing": "ease_in_out",
        "default_zoom": 1.15,
    }
    base.update(overrides)
    return Settings(**base)


def test_easing_functions() -> None:
    assert linear(0.0) == 0.0
    assert linear(1.0) == 1.0
    assert apply_easing("ease_in_out", 0.5) == ease_in_out(0.5)
    assert apply_easing("linear", 1.5) == 1.0


def test_viewport_center_full_image() -> None:
    vp = viewport_for_scale(image_width=1280, image_height=720, scale=1.0)
    assert vp.x == 0.0
    assert vp.y == 0.0
    assert vp.width == 1280.0
    assert vp.height == 720.0


def test_viewport_zoom_in_reduces_crop() -> None:
    vp = viewport_for_scale(image_width=1280, image_height=720, scale=2.0)
    assert vp.width == 640.0
    assert vp.height == 360.0
    assert vp.x == 320.0
    assert vp.y == 180.0


def test_zoom_below_one_rejected() -> None:
    with pytest.raises(ValidationAppError) as exc:
        viewport_for_scale(image_width=100, image_height=100, scale=0.9)
    assert exc.value.code == "CAMERA_INVALID_ZOOM"


def test_viewport_out_of_bounds_rejected() -> None:
    bad = Viewport(x=900.0, y=0.0, width=500.0, height=720.0)
    with pytest.raises(ValidationAppError) as exc:
        validate_viewport(
            bad,
            image_width=1280,
            image_height=720,
            output_width=1280,
            output_height=720,
        )
    assert exc.value.code == "CAMERA_VIEWPORT_OUT_OF_BOUNDS"


def test_aspect_ratio_mismatch_rejected() -> None:
    bad = Viewport(x=0.0, y=0.0, width=500.0, height=500.0)
    with pytest.raises(ValidationAppError) as exc:
        validate_viewport(
            bad,
            image_width=1280,
            image_height=720,
            output_width=1280,
            output_height=720,
        )
    assert exc.value.code == "CAMERA_ASPECT_RATIO_MISMATCH"


def test_camera_zoom_in_interpolation() -> None:
    camera = CameraService(
        config=CameraConfig(
            type=CameraType.ZOOM_IN,
            start_scale=1.0,
            end_scale=1.25,
            duration=60,
            easing="linear",
        ),
        image_width=1280,
        image_height=720,
    )
    start = camera.viewport_at_time(0.0)
    end = camera.viewport_at_time(60.0)
    assert start.width == 1280.0
    assert end.width == pytest.approx(1280.0 / 1.25)
    assert end.width < start.width


def test_camera_pan_left_moves_viewport() -> None:
    camera = CameraService(
        config=CameraConfig(
            type=CameraType.PAN_LEFT,
            start_scale=1.25,
            end_scale=1.25,
            duration=10,
            easing="linear",
        ),
        image_width=1280,
        image_height=720,
    )
    first = camera.viewport_at_time(0.0)
    last = camera.viewport_at_time(10.0)
    assert last.x < first.x


def test_default_camera_config_is_center() -> None:
    cfg = default_camera_config(_settings(Path(".")), duration_sec=30)
    assert cfg.type == CameraType.CENTER
    assert cfg.start_scale == 1.0
    assert cfg.end_scale == 1.0


def test_default_camera_config_uses_settings_zoom_in(tmp_path: Path) -> None:
    cfg = default_camera_config(
        _settings(tmp_path, default_camera="zoom_in", default_zoom=1.15),
        duration_sec=60,
    )
    assert cfg.type == CameraType.ZOOM_IN
    assert cfg.start_scale == 1.0
    assert cfg.end_scale == 1.15
    assert cfg.easing == "ease_in_out"


def test_camera_metadata_generation() -> None:
    camera = CameraService(
        config=CameraConfig(
            type=CameraType.ZOOM_IN,
            start_scale=1.0,
            end_scale=1.15,
            duration=60,
            easing="ease_in_out",
        ),
        image_width=1280,
        image_height=720,
    )
    meta = camera.metadata()
    data = json.loads(meta.model_dump_json())
    assert data["camera_type"] == "zoom_in"
    assert data["start_scale"] == 1.0
    assert data["end_scale"] == 1.15
    assert data["zoom"] == 1.15
    assert data["easing"] == "ease_in_out"


def test_load_camera_json_from_project(tmp_path: Path) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    fs = ProjectFilesystem(_settings(tmp_path))
    root = fs.project_root(project_id)
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "camera.json").write_text(
        json.dumps(
            {
                "type": "zoom_in",
                "start_scale": 1.0,
                "end_scale": 1.2,
                "duration": 60,
                "easing": "ease_out",
            }
        ),
        encoding="utf-8",
    )
    camera = CameraService.from_project(
        root,
        _settings(tmp_path),
        duration_sec=30,
        image_width=100,
        image_height=100,
    )
    assert camera.config.type == CameraType.ZOOM_IN
    assert camera.config.duration == 30
    assert camera.config.end_scale == 1.2


def test_render_frame_writes_output(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    from app.features.renderer.frame_renderer import render_frame

    source = tmp_path / "src.png"
    source.write_bytes(_minimal_png(size=(2, 2)))
    dest = tmp_path / "frame.png"
    viewport = Viewport(x=0.0, y=0.0, width=2.0, height=2.0)
    render_frame(
        source_image=source,
        viewport=viewport,
        output_size=(2, 2),
        dest=dest,
    )
    assert dest.is_file()
    assert dest.stat().st_size > 0
    from PIL import Image

    with Image.open(dest) as frame:
        assert frame.size == (2, 2)


def test_lerp() -> None:
    assert lerp(1.0, 2.0, 0.5) == 1.5
