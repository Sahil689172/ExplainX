"""Keyframe generation from animation clips."""

from __future__ import annotations

from typing import Sequence

from animation.animation_metadata import AnimationClip, AnimationType, Keyframe
from animation.easing import Easing
from image_generation.logger import get_engine_logger


class KeyframeGenerator:
    """Generate position / scale / rotation / opacity / camera keyframes."""

    def __init__(self, *, easing: Easing | None = None, logger=None) -> None:
        self._easing = easing or Easing()
        self._log = logger or get_engine_logger("animation")

    def generate(
        self,
        animations: Sequence[AnimationClip],
        *,
        bounds: dict[str, dict[str, float]] | None = None,
        steps_per_clip: int = 5,
    ) -> list[Keyframe]:
        bounds = bounds or {}
        keyframes: list[Keyframe] = []
        for clip in animations:
            b = bounds.get(clip.target, {"x": 0, "y": 0, "width": 100, "height": 100})
            base_x = b.get("x", 0.0)
            base_y = b.get("y", 0.0)
            kfs = self._keyframes_for_clip(clip, base_x, base_y, steps=steps_per_clip)
            keyframes.extend(kfs)
            self._log.info(
                "KEYFRAME_GENERATED target=%s count=%s type=%s",
                clip.target,
                len(kfs),
                clip.animation_type.value,
            )
        keyframes.sort(key=lambda k: (k.target, k.time))
        return keyframes

    def _keyframes_for_clip(
        self,
        clip: AnimationClip,
        base_x: float,
        base_y: float,
        *,
        steps: int,
    ) -> list[Keyframe]:
        out: list[Keyframe] = []
        if clip.duration <= 0:
            return out
        for i in range(steps):
            t_norm = i / max(steps - 1, 1)
            time = clip.start_time + clip.duration * t_norm
            opacity, scale, rotation, pos = self._state_at(
                clip.animation_type, t_norm, base_x, base_y, clip.easing
            )
            out.append(
                Keyframe(
                    time=round(time, 4),
                    target=clip.target,
                    position=pos,
                    scale=scale,
                    rotation=rotation,
                    opacity=round(opacity, 4),
                )
            )
        return out

    def _state_at(
        self,
        anim_type: AnimationType,
        t_norm: float,
        base_x: float,
        base_y: float,
        easing: str,
    ) -> tuple[float, tuple[float, float], float, tuple[float, float]]:
        p = self._easing.interpolate(t_norm, easing)
        opacity = 1.0
        scale = (1.0, 1.0)
        rotation = 0.0
        x, y = base_x, base_y

        if anim_type == AnimationType.FADE_IN:
            opacity = p
        elif anim_type == AnimationType.FADE_OUT:
            opacity = 1.0 - p
        elif anim_type == AnimationType.SLIDE_LEFT:
            opacity = min(1.0, p * 1.2)
            x = base_x + (1 - p) * 80
        elif anim_type == AnimationType.SLIDE_RIGHT:
            opacity = min(1.0, p * 1.2)
            x = base_x - (1 - p) * 80
        elif anim_type == AnimationType.SLIDE_UP:
            opacity = min(1.0, p * 1.2)
            y = base_y + (1 - p) * 60
        elif anim_type == AnimationType.SLIDE_DOWN:
            opacity = min(1.0, p * 1.2)
            y = base_y - (1 - p) * 60
        elif anim_type == AnimationType.ZOOM_IN:
            opacity = p
            s = 0.85 + 0.15 * p
            scale = (s, s)
        elif anim_type == AnimationType.ZOOM_OUT:
            opacity = 1.0
            s = 1.0 + 0.1 * p
            scale = (s, s)
        elif anim_type == AnimationType.SCALE:
            s = 0.9 + 0.1 * p
            scale = (s, s)
        elif anim_type == AnimationType.ROTATE:
            rotation = p * 5.0
        elif anim_type == AnimationType.HIGHLIGHT:
            opacity = 1.0
            s = 1.0 + 0.03 * math_sin_pulse(p)
            scale = (s, s)
        elif anim_type == AnimationType.PULSE:
            s = 1.0 + 0.05 * math_sin_pulse(p)
            scale = (s, s)
        elif anim_type in (AnimationType.DRAW_ARROW, AnimationType.WRITE_LABEL):
            opacity = p
        elif anim_type == AnimationType.SEQUENTIAL_REVEAL:
            opacity = 1.0 if p > 0.1 else 0.0

        return opacity, scale, rotation, (x, y)


def math_sin_pulse(p: float) -> float:
    import math

    return math.sin(p * math.pi * 2)
