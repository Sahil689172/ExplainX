"""Easing curves for animation interpolation (metadata names + sample values)."""

from __future__ import annotations

import math
from enum import Enum
from typing import Callable


class EasingName(str, Enum):
    LINEAR = "linear"
    EASE_IN = "ease-in"
    EASE_OUT = "ease-out"
    EASE_IN_OUT = "ease-in-out"
    EASE_IN_CUBIC = "ease-in-cubic"
    EASE_OUT_CUBIC = "ease-out-cubic"


_EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    EasingName.LINEAR.value: lambda t: t,
    EasingName.EASE_IN.value: lambda t: t * t,
    EasingName.EASE_OUT.value: lambda t: t * (2 - t),
    EasingName.EASE_IN_OUT.value: lambda t: 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t,
    EasingName.EASE_IN_CUBIC.value: lambda t: t**3,
    EasingName.EASE_OUT_CUBIC.value: lambda t: 1 - (1 - t) ** 3,
}


class Easing:
    """Resolve easing names and interpolate values for keyframe generation."""

    DEFAULT = EasingName.EASE_IN_OUT.value

    def resolve(self, name: str | None) -> str:
        if not name:
            return self.DEFAULT
        key = name.strip().lower()
        return key if key in _EASING_FUNCTIONS else self.DEFAULT

    def interpolate(self, t: float, easing: str | None = None) -> float:
        """Return eased progress in [0, 1] for normalized time t."""
        t = max(0.0, min(1.0, t))
        fn = _EASING_FUNCTIONS.get(self.resolve(easing), _EASING_FUNCTIONS[self.DEFAULT])
        return max(0.0, min(1.0, fn(t)))

    def lerp(self, start: float, end: float, t: float, easing: str | None = None) -> float:
        p = self.interpolate(t, easing)
        return start + (end - start) * p

    def sample_curve(self, easing: str | None = None, steps: int = 11) -> list[float]:
        return [round(self.interpolate(i / max(steps - 1, 1), easing), 4) for i in range(steps)]
