"""Type definitions for the Phase 6.0 frame rendering engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LayerType(str, Enum):
    BACKGROUND = "background"
    TITLE = "title"
    SUBTITLE = "subtitle"
    ASSET = "asset"
    DIAGRAM = "diagram"
    LEGEND = "legend"
    BULLETS = "bullet_list"
    FOOTER = "footer"
    CAPTION = "caption"
    CALLOUT = "callout"


@dataclass(slots=True)
class TransformState:
    """2D transform applied to a layer at a point in time."""

    position: tuple[float, float] = (0.0, 0.0)
    scale: tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    opacity: float = 1.0
    anchor: tuple[float, float] = (0.5, 0.5)
    crop: tuple[float, float, float, float] | None = None


@dataclass(slots=True)
class CameraState:
    """Viewport camera at a point in time."""

    zoom: float = 1.0
    pan: tuple[float, float] = (0.0, 0.0)
    focus_region: tuple[float, float, float, float] | None = None
    camera_type: str = "static"


@dataclass(slots=True)
class RenderLayer:
    """A layer ready for rendering."""

    layer_id: str
    layer_type: LayerType
    content: str = ""
    image_path: str | None = None
    bullets: list[str] = field(default_factory=list)
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)
    transform: TransformState = field(default_factory=TransformState)
    visible: bool = True
    z_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
