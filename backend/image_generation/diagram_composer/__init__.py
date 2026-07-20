"""Phase 5.7 — Educational Diagram Composer.

Transforms generated illustrations into complete educational diagrams with
programmatic labels, arrows, callouts, and legends.

Diffusion models produce illustrations only; ExplainX composes diagrams.
"""

from image_generation.diagram_composer.canvas import Canvas, load_illustration
from image_generation.diagram_composer.diagram_engine import DiagramEngine
from image_generation.diagram_composer.elements import (
    Anchor,
    DiagramSpec,
    DiagramType,
    LayoutMode,
    LegendItem,
)
from image_generation.diagram_composer.export_manager import ExportFormat, ExportManager
from image_generation.diagram_composer.fixtures import (
    FIXTURES,
    dna_spec,
    earth_spec,
    get_fixture,
    human_heart_spec,
    motherboard_spec,
    photosynthesis_spec,
)
from image_generation.diagram_composer.geometry import BoundingBox, Point, Rect
from image_generation.diagram_composer.layout_engine import LayoutEngine
from image_generation.diagram_composer.object_locator import (
    ManualObjectLocator,
    NullObjectLocator,
    ObjectLocator,
    make_anchor,
)
from image_generation.diagram_composer.theme_manager import DiagramTheme, ThemeManager

__all__ = [
    "Anchor",
    "BoundingBox",
    "Canvas",
    "DiagramEngine",
    "DiagramSpec",
    "DiagramTheme",
    "DiagramType",
    "ExportFormat",
    "ExportManager",
    "FIXTURES",
    "LayoutEngine",
    "LayoutMode",
    "LegendItem",
    "ManualObjectLocator",
    "NullObjectLocator",
    "ObjectLocator",
    "Point",
    "Rect",
    "ThemeManager",
    "dna_spec",
    "earth_spec",
    "get_fixture",
    "human_heart_spec",
    "load_illustration",
    "make_anchor",
    "motherboard_spec",
    "photosynthesis_spec",
]
