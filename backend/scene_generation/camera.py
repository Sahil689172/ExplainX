"""Camera metadata for future animation (Ken Burns, pan, zoom, focus)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from image_generation.diagram_composer.geometry import Rect


@dataclass(slots=True)
class CameraState:
    """Static camera frame — start and end for future interpolation."""

    camera_start: tuple[float, float]
    camera_end: tuple[float, float]
    zoom: float = 1.0
    pan: tuple[float, float] = (0.0, 0.0)
    focus_region: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CameraEvent:
    """Timed camera keyframe for the animation engine (future)."""

    time_seconds: float
    zoom: float
    pan: tuple[float, float]
    focus_region: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CameraPlanner:
    """Generate camera metadata from scene layout without rendering animation."""

    def plan(
        self,
        *,
        canvas_width: int,
        canvas_height: int,
        focus_rect: Rect | None = None,
        scene_type: str = "single_concept",
    ) -> dict[str, Any]:
        cx, cy = canvas_width / 2, canvas_height / 2
        focus = focus_rect or Rect(
            canvas_width * 0.2,
            canvas_height * 0.15,
            canvas_width * 0.6,
            canvas_height * 0.65,
        )
        zoom = 1.05 if scene_type in {"single_concept", "process"} else 1.0
        state = CameraState(
            camera_start=(cx, cy),
            camera_end=(focus.center.x, focus.center.y),
            zoom=zoom,
            pan=(0.0, 0.0),
            focus_region=(
                focus.x / canvas_width,
                focus.y / canvas_height,
                focus.width / canvas_width,
                focus.height / canvas_height,
            ),
        )
        events = [
            CameraEvent(0.0, zoom=1.0, pan=(0.0, 0.0), focus_region=state.focus_region),
            CameraEvent(
                2.5,
                zoom=zoom,
                pan=(state.camera_end[0] - cx, state.camera_end[1] - cy),
                focus_region=state.focus_region,
            ),
        ]
        return {
            "camera_start": state.camera_start,
            "camera_end": state.camera_end,
            "zoom": state.zoom,
            "pan": state.pan,
            "focus_region": state.focus_region,
            "camera_events": [e.to_dict() for e in events],
        }
