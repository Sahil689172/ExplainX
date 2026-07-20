"""Camera interpolation for frame rendering."""

from __future__ import annotations

from animation.easing import Easing
from video_renderer.renderer_types import CameraState


class CameraRenderer:
    """Resolve pan, zoom, focus, and Ken Burns at a given time."""

    def __init__(self, *, easing: Easing | None = None) -> None:
        self._easing = easing or Easing()

    def camera_at(
        self,
        timeline: dict,
        time_s: float,
        *,
        scene_camera: dict | None = None,
    ) -> CameraState:
        keyframes = timeline.get("keyframes") or []
        cam_kfs = [k for k in keyframes if k.get("target") == "__camera__" and k.get("camera")]
        if cam_kfs:
            return self._from_keyframes(cam_kfs, time_s)

        events = timeline.get("camera_events") or (scene_camera or {}).get("camera_events") or []
        if events:
            return self._from_events(events, time_s, scene_camera or {})

        return CameraState(
            zoom=float((scene_camera or {}).get("zoom", 1.0)),
            pan=tuple((scene_camera or {}).get("pan", (0.0, 0.0))),
            focus_region=(scene_camera or {}).get("focus_region"),
        )

    def _from_keyframes(self, kfs: list[dict], time_s: float) -> CameraState:
        kfs.sort(key=lambda k: k["time"])
        if time_s <= kfs[0]["time"]:
            return self._kf_to_state(kfs[0])
        if time_s >= kfs[-1]["time"]:
            return self._kf_to_state(kfs[-1])
        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a["time"] <= time_s <= b["time"]:
                span = b["time"] - a["time"]
                t = (time_s - a["time"]) / span if span > 0 else 0.0
                sa, sb = self._kf_to_state(a), self._kf_to_state(b)
                return CameraState(
                    zoom=self._easing.lerp(sa.zoom, sb.zoom, t),
                    pan=(
                        self._easing.lerp(sa.pan[0], sb.pan[0], t),
                        self._easing.lerp(sa.pan[1], sb.pan[1], t),
                    ),
                    focus_region=sa.focus_region or sb.focus_region,
                    camera_type=sb.camera_type,
                )
        return self._kf_to_state(kfs[-1])

    def _kf_to_state(self, kf: dict) -> CameraState:
        cam = kf.get("camera") or {}
        pan = cam.get("pan", (0.0, 0.0))
        return CameraState(
            zoom=float(cam.get("zoom", 1.0)),
            pan=(float(pan[0]), float(pan[1])),
            focus_region=cam.get("focus_region"),
            camera_type=str(cam.get("camera_type", "static")),
        )

    def _from_events(
        self, events: list[dict], time_s: float, scene_camera: dict
    ) -> CameraState:
        events = sorted(events, key=lambda e: e.get("time_seconds", e.get("start_time", 0.0)))
        active = events[0]
        for ev in events:
            t = float(ev.get("time_seconds", ev.get("start_time", 0.0)))
            if t <= time_s:
                active = ev
        pan = active.get("pan", (0.0, 0.0))
        return CameraState(
            zoom=float(active.get("zoom", scene_camera.get("zoom", 1.0))),
            pan=(float(pan[0]), float(pan[1])),
            focus_region=active.get("focus_region") or scene_camera.get("focus_region"),
            camera_type=str(active.get("camera_type", "ken_burns")),
        )

    def apply_viewport(
        self,
        image,
        camera: CameraState,
        *,
        width: int,
        height: int,
    ):
        """Apply zoom/pan crop to a composited frame (PIL Image)."""
        from PIL import Image

        if camera.zoom <= 1.0001 and camera.pan == (0.0, 0.0):
            return image

        # Cinematic clamp: never zoom beyond 1.10 — no aggressive motion.
        zoom = max(1.0, min(camera.zoom, 1.10))
        scaled_w = round(width * zoom)
        scaled_h = round(height * zoom)
        scaled = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

        # Float centering + single rounding avoids the 1px frame-to-frame jitter.
        cx = (scaled_w - width) / 2.0 + float(camera.pan[0])
        cy = (scaled_h - height) / 2.0 + float(camera.pan[1])
        cx = int(round(max(0.0, min(cx, float(scaled_w - width)))))
        cy = int(round(max(0.0, min(cy, float(scaled_h - height)))))
        return scaled.crop((cx, cy, cx + width, cy + height))
