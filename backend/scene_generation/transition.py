"""Scene transition metadata for future slide / video transitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class TransitionType(str, Enum):
    NONE = "none"
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM = "zoom"
    DISSOLVE = "dissolve"


@dataclass(slots=True)
class Transition:
    """Transition between scenes (future video renderer)."""

    transition_type: TransitionType = TransitionType.FADE
    duration_seconds: float = 0.5
    easing: str = "ease-in-out"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
