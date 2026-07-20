"""Camera animation expansion from scene JSON camera metadata."""

from __future__ import annotations

from typing import Any, Sequence
from uuid import uuid4

from animation.animation_metadata import CameraAnimationEvent, CameraAnimationType
from animation.easing import Easing
from image_generation.logger import get_engine_logger


class CameraAnimationEngine:
    """Convert scene camera metadata into timed camera animation events."""

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
        events: list[CameraAnimationEvent] = []
        raw_events = scene_camera.get("camera_events") or []
        if raw_events:
            for raw in raw_events:
                events.append(self._from_raw(raw, duration))
        else:
            events.append(
                CameraAnimationEvent(
                    event_id=str(uuid4()),
                    camera_type=preset_camera,
                    start_time=0.0,
                    end_time=duration,
                    zoom=float(scene_camera.get("zoom", 1.0)),
                    pan=tuple(scene_camera.get("pan", (0.0, 0.0))),
                    focus_region=scene_camera.get("focus_region"),
                    follow_target=follow_target,
                )
            )

        if preset_camera == CameraAnimationType.KEN_BURNS and len(events) == 1:
            ev = events[0]
            end_pt = scene_camera.get("camera_end", (ev.pan[0], ev.pan[1]))
            start_pt = scene_camera.get("camera_start", (0.0, 0.0))
            if isinstance(end_pt, (list, tuple)) and isinstance(start_pt, (list, tuple)):
                pan_delta = (float(end_pt[0]) - float(start_pt[0]), float(end_pt[1]) - float(start_pt[1]))
            else:
                pan_delta = ev.pan
            events.append(
                CameraAnimationEvent(
                    event_id=str(uuid4()),
                    camera_type=CameraAnimationType.KEN_BURNS,
                    start_time=round(duration * 0.15, 3),
                    end_time=duration,
                    zoom=round(ev.zoom * 1.08, 3),
                    pan=pan_delta,
                    focus_region=ev.focus_region,
                    follow_target=follow_target or "diagram_main",
                    easing=Easing.DEFAULT,
                )
            )

        for ev in events:
            self._log.info(
                "CAMERA_EVENT type=%s start=%.2f end=%.2f",
                ev.camera_type.value,
                ev.start_time,
                ev.end_time,
            )
        return events

    def _from_raw(self, raw: dict[str, Any], duration: float) -> CameraAnimationEvent:
        t = float(raw.get("time_seconds", 0.0))
        cam_type = CameraAnimationType.KEN_BURNS if raw.get("zoom", 1.0) != 1.0 else CameraAnimationType.PAN
        end = min(duration, t + max(duration * 0.4, 1.0))
        return CameraAnimationEvent(
            event_id=str(uuid4()),
            camera_type=cam_type,
            start_time=t,
            end_time=end,
            zoom=float(raw.get("zoom", 1.0)),
            pan=tuple(raw.get("pan", (0.0, 0.0))),
            focus_region=raw.get("focus_region"),
        )

    def keyframes_for_events(
        self, events: Sequence[CameraAnimationEvent], *, steps: int = 8
    ) -> list[dict[str, Any]]:
        """Global camera keyframes for renderers."""
        frames: list[dict[str, Any]] = []
        for ev in events:
            span = max(ev.end_time - ev.start_time, 0.001)
            for i in range(steps):
                t_norm = i / max(steps - 1, 1)
                time = ev.start_time + span * t_norm
                frames.append(
                    {
                        "time": round(time, 4),
                        "camera_type": ev.camera_type.value,
                        "zoom": round(
                            self._easing.lerp(1.0, ev.zoom, t_norm, ev.easing), 4
                        ),
                        "pan": (
                            round(self._easing.lerp(0.0, ev.pan[0], t_norm, ev.easing), 2),
                            round(self._easing.lerp(0.0, ev.pan[1], t_norm, ev.easing), 2),
                        ),
                        "focus_region": ev.focus_region,
                    }
                )
        return frames
