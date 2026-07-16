"""Easing functions for camera interpolation (t in [0, 1])."""

from __future__ import annotations

from typing import Callable

EASING_NAMES = frozenset({"linear", "ease_in", "ease_out", "ease_in_out"})


def linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    return t * t


def ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - pow(-2.0 * t + 2.0, 2) / 2.0


_EASING_MAP: dict[str, Callable[[float], float]] = {
    "linear": linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
}


def get_easing(name: str) -> Callable[[float], float]:
    key = (name or "linear").strip().lower()
    if key not in _EASING_MAP:
        raise ValueError(f"Unknown easing: {name!r}")
    return _EASING_MAP[key]


def apply_easing(name: str, t: float) -> float:
    """Apply easing to progress ``t`` clamped to [0, 1]."""
    clamped = max(0.0, min(1.0, t))
    return get_easing(name)(clamped)
