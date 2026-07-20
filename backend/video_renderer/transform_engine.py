"""Transform interpolation from animation timeline keyframes."""

from __future__ import annotations

from animation.easing import Easing
from video_renderer.renderer_types import TransformState


class TransformEngine:
    """Apply translate, scale, rotate, opacity, and anchor from timeline keyframes."""

    def __init__(self, *, easing: Easing | None = None) -> None:
        self._easing = easing or Easing()

    def transform_at(
        self,
        keyframes: list[dict],
        target: str,
        time_s: float,
        *,
        base_bounds: tuple[float, float, float, float],
        base_position: tuple[float, float] | None = None,
    ) -> TransformState:
        kfs = [k for k in keyframes if k.get("target") == target and k.get("camera") is None]
        bx, by, bw, bh = base_bounds
        default_pos = base_position if base_position else (bx, by)

        if not kfs:
            return TransformState(
                position=default_pos,
                scale=(1.0, 1.0),
                rotation=0.0,
                opacity=1.0,
            )

        kfs.sort(key=lambda k: k["time"])
        if time_s <= kfs[0]["time"]:
            return self._from_keyframe(kfs[0], default_pos)
        if time_s >= kfs[-1]["time"]:
            return self._from_keyframe(kfs[-1], default_pos)

        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a["time"] <= time_s <= b["time"]:
                span = b["time"] - a["time"]
                t = (time_s - a["time"]) / span if span > 0 else 0.0
                return self._lerp_states(self._from_keyframe(a, default_pos), self._from_keyframe(b, default_pos), t)

        return self._from_keyframe(kfs[-1], default_pos)

    def _from_keyframe(
        self, kf: dict, default_pos: tuple[float, float]
    ) -> TransformState:
        pos = kf.get("position", default_pos)
        scale = kf.get("scale", (1.0, 1.0))
        return TransformState(
            position=(float(pos[0]), float(pos[1])),
            scale=(float(scale[0]), float(scale[1])),
            rotation=float(kf.get("rotation", 0.0)),
            opacity=float(kf.get("opacity", 1.0)),
        )

    def _lerp_states(self, a: TransformState, b: TransformState, t: float) -> TransformState:
        e = self._easing
        return TransformState(
            position=(
                e.lerp(a.position[0], b.position[0], t),
                e.lerp(a.position[1], b.position[1], t),
            ),
            scale=(
                e.lerp(a.scale[0], b.scale[0], t),
                e.lerp(a.scale[1], b.scale[1], t),
            ),
            rotation=e.lerp(a.rotation, b.rotation, t),
            opacity=e.lerp(a.opacity, b.opacity, t),
            anchor=a.anchor,
        )
