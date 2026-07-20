"""Diagram element models and metadata schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from image_generation.diagram_composer.geometry import BoundingBox, Point, Rect


class DiagramType(str, Enum):
    OBJECT = "object"
    BIOLOGY = "biology"
    FLOW = "flow"
    PROCESS = "process"
    ANATOMY = "anatomy"
    COMPUTER_ARCHITECTURE = "computer_architecture"
    PHYSICS_CONCEPT = "physics_concept"
    CHEMISTRY = "chemistry"
    SIMPLE_INFOGRAPHIC = "simple_infographic"


class LayoutMode(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    RADIAL = "radial"
    AUTOMATIC = "automatic"


class ArrowStyle(str, Enum):
    STRAIGHT = "straight"
    CURVED = "curved"
    DOUBLE = "double"
    DASHED = "dashed"
    LEADER = "leader"


@dataclass(slots=True)
class Anchor:
    """Manual placement target for a labeled region."""

    id: str
    center: Point
    label: str
    bbox: BoundingBox | None = None
    color_hint: str | None = None
    description: str | None = None


@dataclass(slots=True)
class PlacedLabel:
    """A label after layout resolution."""

    id: str
    text: str
    position: Point
    bounds: Rect
    anchor_id: str
    font_size: int = 14
    bold: bool = False
    italic: bool = False
    lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlacedArrow:
    """An arrow / leader after layout resolution."""

    id: str
    start: Point
    end: Point
    style: ArrowStyle = ArrowStyle.LEADER
    control: Point | None = None
    double_headed: bool = False
    dashed: bool = False
    label_id: str | None = None
    anchor_id: str | None = None


@dataclass(slots=True)
class LegendItem:
    key: str
    description: str
    swatch_color: tuple[int, int, int, int] | None = None
    symbol: str = "circle"


@dataclass(slots=True)
class LegendBlock:
    items: list[LegendItem]
    bounds: Rect
    title: str = "Legend"


@dataclass(slots=True)
class DiagramMetadata:
    """Persisted diagram metadata for repository / export referencing."""

    diagram_id: str
    concept: str
    subject: str
    diagram_type: str
    canvas_size: tuple[int, int]
    labels: list[dict[str, Any]]
    arrows: list[dict[str, Any]]
    theme: str
    created_at: str
    export_format: str
    concept_id: str | None = None
    asset_version: str | None = None
    illustration_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def create(
        *,
        concept: str,
        subject: str,
        diagram_type: DiagramType,
        canvas_size: tuple[int, int],
        labels: list[PlacedLabel],
        arrows: list[PlacedArrow],
        theme: str,
        export_format: str,
        concept_id: str | None = None,
        asset_version: str | None = None,
        illustration_path: str | None = None,
    ) -> DiagramMetadata:
        return DiagramMetadata(
            diagram_id=str(uuid4()),
            concept=concept,
            subject=subject,
            diagram_type=diagram_type.value,
            canvas_size=canvas_size,
            labels=[
                {
                    "id": lb.id,
                    "text": lb.text,
                    "x": lb.position.x,
                    "y": lb.position.y,
                    "anchor_id": lb.anchor_id,
                }
                for lb in labels
            ],
            arrows=[
                {
                    "id": ar.id,
                    "style": ar.style.value,
                    "start": ar.start.as_tuple(),
                    "end": ar.end.as_tuple(),
                    "label_id": ar.label_id,
                    "anchor_id": ar.anchor_id,
                }
                for ar in arrows
            ],
            theme=theme,
            created_at=datetime.now(timezone.utc).isoformat(),
            export_format=export_format,
            concept_id=concept_id,
            asset_version=asset_version,
            illustration_path=illustration_path,
        )


@dataclass(slots=True)
class DiagramSpec:
    """Input specification for composing one educational diagram."""

    concept: str
    subject: str = "General"
    diagram_type: DiagramType = DiagramType.OBJECT
    title: str | None = None
    subtitle: str | None = None
    caption: str | None = None
    anchors: list[Anchor] = field(default_factory=list)
    legend_items: list[LegendItem] = field(default_factory=list)
    layout: LayoutMode = LayoutMode.AUTOMATIC
    theme: str = "textbook"
    width: int = 1024
    height: int = 768
    padding: int = 48
    margin: int = 24
    transparent_background: bool = False
    show_legend: bool = True
    show_title: bool = True
    concept_id: str | None = None
    asset_version: str | None = None


@dataclass(slots=True)
class DiagramResult:
    """Output of a compose + export pass."""

    metadata: DiagramMetadata
    png_path: str | None = None
    svg_path: str | None = None
    labels: list[PlacedLabel] = field(default_factory=list)
    arrows: list[PlacedArrow] = field(default_factory=list)
    legend: LegendBlock | None = None
