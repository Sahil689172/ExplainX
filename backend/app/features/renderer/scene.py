"""Scene composition helpers."""

from __future__ import annotations

from pathlib import Path

from app.features.renderer.camera_schemas import CameraType
from app.features.renderer.scene_schemas import SceneDefinition

_CAMERA_LABELS = {
    CameraType.CENTER: "Center",
    CameraType.ZOOM_IN: "Zoom In",
    CameraType.ZOOM_OUT: "Zoom Out",
    CameraType.PAN_LEFT: "Pan Left",
    CameraType.PAN_RIGHT: "Pan Right",
    CameraType.PAN_UP: "Pan Up",
    CameraType.PAN_DOWN: "Pan Down",
}


def scene_frame_count(*, duration_sec: int, fps: int) -> int:
    """Frames for one scene at ``fps``."""
    return int(duration_sec) * int(fps)


def total_frame_count(scenes: list[SceneDefinition], *, fps: int) -> int:
    return sum(scene_frame_count(duration_sec=s.duration, fps=fps) for s in scenes)


def camera_label(camera: CameraType) -> str:
    return _CAMERA_LABELS.get(camera, camera.value)


def log_scene(
    *,
    index: int,
    total: int,
    scene: SceneDefinition,
    frames: int,
) -> None:
    """Print per-scene render banner."""
    image_name = Path(scene.image).name
    print("[Scene]", flush=True)
    print(f"Scene {index} / {total}", flush=True)
    print(f"Image {image_name}", flush=True)
    print(f"Duration {scene.duration} sec", flush=True)
    print(f"Frames {frames}", flush=True)
    print(f"Camera {camera_label(scene.camera)}", flush=True)
