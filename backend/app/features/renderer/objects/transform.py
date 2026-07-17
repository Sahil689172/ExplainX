"""2D transform for scene objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Transform:
    """Position, scale, rotation, and visibility for a sprite."""

    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0  # degrees, clockwise-positive for Pillow rotate(-r)
    opacity: float = 1.0
    visible: bool = True

    def __post_init__(self) -> None:
        if self.scale <= 0.0:
            raise ValueError(f"scale must be > 0, got {self.scale}")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError(f"opacity must be in [0, 1], got {self.opacity}")
