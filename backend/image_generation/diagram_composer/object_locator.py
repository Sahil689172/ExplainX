"""Object location interface — detection is future work; manual anchors work now.

Future implementations may wrap SAM, YOLO, GroundingDINO, or Florence without
changing :class:`~image_generation.diagram_composer.diagram_engine.DiagramEngine`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from image_generation.diagram_composer.elements import Anchor
from image_generation.diagram_composer.geometry import BoundingBox, Point


class ObjectLocator(ABC):
    """Locate labeled regions on an illustration.

    Phase 5.7 ships only :class:`ManualObjectLocator`. Detection backends
    implement this interface later.
    """

    @abstractmethod
    def locate(
        self,
        illustration_path: str | Path,
        *,
        hints: Sequence[str] | None = None,
    ) -> list[Anchor]:
        """Return anchors for objects found (or provided) on the illustration."""


class ManualObjectLocator(ObjectLocator):
    """Deterministic locator that returns caller-supplied anchors unchanged."""

    def __init__(self, anchors: Sequence[Anchor] | None = None) -> None:
        self._anchors = list(anchors or [])

    def set_anchors(self, anchors: Sequence[Anchor]) -> None:
        self._anchors = list(anchors)

    def locate(
        self,
        illustration_path: str | Path,
        *,
        hints: Sequence[str] | None = None,
    ) -> list[Anchor]:
        _ = illustration_path, hints  # unused — manual only
        return list(self._anchors)


class NullObjectLocator(ObjectLocator):
    """Placeholder for future AI detection — currently returns no anchors."""

    def locate(
        self,
        illustration_path: str | Path,
        *,
        hints: Sequence[str] | None = None,
    ) -> list[Anchor]:
        _ = illustration_path, hints
        return []


def make_anchor(
    anchor_id: str,
    label: str,
    *,
    x: float,
    y: float,
    bbox: BoundingBox | None = None,
    color_hint: str | None = None,
    description: str | None = None,
) -> Anchor:
    """Convenience factory for manual anchors."""
    return Anchor(
        id=anchor_id,
        center=Point(x, y),
        label=label,
        bbox=bbox,
        color_hint=color_hint,
        description=description,
    )
