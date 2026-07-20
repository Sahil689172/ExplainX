"""Camera animation expansion from scene JSON camera metadata."""

from __future__ import annotations

from typing import Any, Sequence
from uuid import uuid4

from animation.animation_metadata import CameraAnimationEvent, CameraAnimationType
from animation.easing import Easing
from image_generation.logger import get_engine_logger


class CameraAnimationEngine:
    """Convert scene camera metadata into ONE smooth cinematic camera move.

    A single continuous Ken Burns / zoom track is produced per scene. Overlapping
    or resetting camera events (which caused the "earthquake" jitter) are collapsed
    into a monotonic path with constrained zoom and slow, bounded pan.
    """

    # Cinematic constraints — max zoom 1.10, smooth bezier-like easing.
    MIN_ZOOM = 1.0
    MAX_ZOOM = 1.10
    DEFAULT_ZOOM = 1.06
    CAMERA_EASING = "ease-in-out-quart"
    MAX_PAN_PX = 24.0
    PAN_SCALE = 0.10

    def __init__(self, *, easing: Easing | None = None, logger=None) -> None:
        self._easing = easing or Easing()
        self._log = logger or get_engine_logger("animation")

    def build(
        self,
        scene_camera: dict[str, Any],
        *,
        duration: float,
        preset_camera: CameraAnimationType = CameraAnimationType.KEN_BURNS,
        follow_target: str | None = None,
    ) -> list[CameraAnimationEvent]:
        if preset_camera == CameraAnimationType.STATIC:
            target_zoom = 1.0
            cam_type = CameraAnimationType.STATIC
        else:
            requested = float(scene_camera.get("zoom", self.DEFAULT_ZOOM) or self.DEFAULT_ZOOM)
            if requested <= 1.0:
                requested = self.DEFAULT_ZOOM
            target_zoom = max(self.MIN_ZOOM, min(requested, self.MAX_ZOOM))
            cam_type = CameraAnimationType.KEN_BURNS

        event = CameraAnimationEvent(
            event_id=str(uuid4()),
            camera_type=cam_type,
            start_time=0.0,
            end_time=round(duration, 3),
            zoom=round(target_zoom, 4),
            pan=self._bounded_pan(scene_camera),
            focus_region=scene_camera.get("focus_region"),
            follow_target=follow_target,
            easing=self.CAMERA_EASING,
        )
        self._log.info(
            "CAMERA_EVENT type=%s start=%.2f end=%.2f zoom=%.3f pan=%s",
            event.camera_type.value,
            event.start_time,
            event.end_time,
            event.zoom,
            event.pan,
        )
        return [event]

    def _bounded_pan(self, scene_camera: dict[str, Any]) -> tuple[float, float]:
        """Derive a slow, bounded pan vector (no sudden jumps)."""
        start = scene_camera.get("camera_start")
        end = scene_camera.get("camera_end")
        if isinstance(start, (list, tuple)) and isinstance(end, (list, tuple)):
            dx = float(end[0]) - float(start[0])
            dy = float(end[1]) - float(start[1])
        else:
            p = scene_camera.get("pan", (0.0, 0.0))
            dx, dy = float(p[0]), float(p[1])
        dx *= self.PAN_SCALE
        dy *= self.PAN_SCALE
        mag = (dx * dx + dy * dy) ** 0.5
        if mag > self.MAX_PAN_PX and mag > 0:
            scale = self.MAX_PAN_PX / mag
            dx *= scale
            dy *= scale
        return (round(dx, 2), round(dy, 2))

    def keyframes_for_events(
        self, events: Sequence[CameraAnimationEvent], *, steps: int | None = None
    ) -> list[dict[str, Any]]:
        """One continuous, monotonic camera track across the whole scene."""
        if not events:
            return []
        start = min(e.start_time for e in events)
        end = max(e.end_time for e in events)
        span = max(end - start, 0.001)
        primary = max(events, key=lambda e: e.zoom)
        # Dense sampling → smooth bezier-like motion, scaled with duration.
        n = steps or max(24, int(span * 12))
        frames: list[dict[str, Any]] = []
        for i in range(n):
            t_norm = i / max(n - 1, 1)
            p = self._easing.interpolate(t_norm, primary.easing)
            frames.append(
                {
                    "time": round(start + span * t_norm, 4),
                    "camera_type": primary.camera_type.value,
                    "zoom": round(1.0 + (primary.zoom - 1.0) * p, 5),
                    "pan": (
                        round(primary.pan[0] * p, 3),
                        round(primary.pan[1] * p, 3),
                    ),
                    "focus_region": primary.focus_region,
                }
            )
        return frames
