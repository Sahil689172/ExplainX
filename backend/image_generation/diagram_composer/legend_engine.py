"""Legend engine — auto-generate educational diagram legends."""

from __future__ import annotations

from typing import Sequence

from image_generation.diagram_composer.canvas import Canvas
from image_generation.diagram_composer.elements import Anchor, LegendBlock, LegendItem
from image_generation.diagram_composer.geometry import Rect
from image_generation.diagram_composer.theme_manager import ThemeColors
from image_generation.logger import get_engine_logger


# Default swatch colors for common educational concepts
_COLOR_HINTS: dict[str, tuple[int, int, int, int]] = {
    "sun": (255, 200, 50, 255),
    "yellow": (255, 210, 60, 255),
    "water": (60, 140, 220, 255),
    "blue": (60, 140, 220, 255),
    "oxygen": (80, 180, 255, 255),
    "carbon dioxide": (140, 140, 140, 255),
    "grey": (140, 140, 140, 255),
    "gray": (140, 140, 140, 255),
    "chloroplast": (80, 170, 80, 255),
    "green": (80, 170, 80, 255),
    "dna": (180, 80, 160, 255),
    "heart": (200, 60, 80, 255),
    "cpu": (60, 60, 80, 255),
    "ram": (80, 120, 200, 255),
    "core": (200, 120, 60, 255),
    "mantle": (200, 100, 60, 255),
    "crust": (120, 90, 60, 255),
}


class LegendEngine:
    """Build legend blocks from explicit items and/or anchor metadata."""

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("image_generation.diagram_composer")

    def build(
        self,
        *,
        items: Sequence[LegendItem] | None = None,
        anchors: Sequence[Anchor] | None = None,
        canvas: Canvas,
        theme: ThemeColors,
        title: str = "Legend",
    ) -> LegendBlock:
        legend_items: list[LegendItem] = list(items or [])
        if not legend_items and anchors:
            legend_items = self._from_anchors(anchors)

        # Size legend box bottom-right inside content bounds
        row_h = 22
        width = 220
        height = 28 + row_h * max(1, len(legend_items))
        content = canvas.content_bounds
        x = content.right - width - 8
        y = content.bottom - height - 8
        bounds = Rect(x, y, float(width), float(height))

        block = LegendBlock(items=legend_items, bounds=bounds, title=title)
        self._log.info("LEGEND_CREATED items=%s", len(legend_items))
        return block

    def _from_anchors(self, anchors: Sequence[Anchor]) -> list[LegendItem]:
        items: list[LegendItem] = []
        for anchor in anchors:
            color = self._resolve_color(anchor)
            symbol = "arrow" if "arrow" in (anchor.description or "").lower() else "circle"
            desc = anchor.description or anchor.label
            items.append(
                LegendItem(
                    key=anchor.label,
                    description=desc,
                    swatch_color=color,
                    symbol=symbol,
                )
            )
        return items

    def _resolve_color(self, anchor: Anchor) -> tuple[int, int, int, int]:
        if anchor.color_hint:
            key = anchor.color_hint.strip().lower()
            if key in _COLOR_HINTS:
                return _COLOR_HINTS[key]
            if key.startswith("#") and len(key) == 7:
                r = int(key[1:3], 16)
                g = int(key[3:5], 16)
                b = int(key[5:7], 16)
                return (r, g, b, 255)
        label_key = anchor.label.lower()
        for hint, color in _COLOR_HINTS.items():
            if hint in label_key:
                return color
        return (100, 100, 100, 255)
