"""Layout engine — place labels without overlap / cropping."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from image_generation.diagram_composer.canvas import Canvas
from image_generation.diagram_composer.elements import (
    Anchor,
    ArrowStyle,
    LayoutMode,
    PlacedArrow,
    PlacedLabel,
)
from image_generation.diagram_composer.geometry import Point, Rect
from image_generation.diagram_composer.label_engine import LabelEngine, LabelStyle
from image_generation.logger import get_engine_logger


@dataclass(slots=True)
class LayoutResult:
    labels: list[PlacedLabel]
    arrows: list[PlacedArrow]
    layout_mode: LayoutMode


class LayoutEngine:
    """Automatically place labels around illustration anchors."""

    def __init__(
        self,
        label_engine: LabelEngine | None = None,
        *,
        logger=None,
    ) -> None:
        self._labels = label_engine or LabelEngine()
        self._log = logger or get_engine_logger("image_generation.diagram_composer")

    def layout(
        self,
        anchors: Sequence[Anchor],
        canvas: Canvas,
        illustration_rect: Rect,
        *,
        mode: LayoutMode = LayoutMode.AUTOMATIC,
    ) -> LayoutResult:
        effective = mode
        if mode == LayoutMode.AUTOMATIC:
            effective = self._choose_mode(len(anchors))
        self._log.info("LAYOUT_SELECTED mode=%s anchors=%s", effective.value, len(anchors))

        placed_labels: list[PlacedLabel] = []
        placed_arrows: list[PlacedArrow] = []
        occupied: list[Rect] = []

        n = len(anchors)
        for index, anchor in enumerate(anchors):
            # Map normalized-ish centers: if coords look like 0–1, scale into illustration
            center = self._resolve_anchor_point(anchor, illustration_rect)
            preferred = self._candidate_positions(
                effective, index, n, center, illustration_rect, canvas.content_bounds
            )
            label_style = LabelStyle(font_size=14, max_width=150, bold=False)
            lines, raw_bounds = self._labels.make_bounds(
                anchor.label, preferred[0], style=label_style
            )
            bounds = self._place_without_overlap(
                raw_bounds, preferred, occupied, canvas.content_bounds
            )
            occupied.append(bounds.inflate(4))

            label = PlacedLabel(
                id=f"label_{anchor.id}",
                text=anchor.label,
                position=Point(bounds.x + 6, bounds.y + 4),
                bounds=bounds,
                anchor_id=anchor.id,
                font_size=label_style.font_size,
                lines=lines,
            )
            placed_labels.append(label)
            self._log.info(
                "LABEL_PLACED id=%s text=%r x=%.1f y=%.1f",
                label.id,
                label.text,
                bounds.x,
                bounds.y,
            )

            # Leader from label edge toward anchor
            label_attach = self._nearest_edge_point(bounds, center)
            arrow = PlacedArrow(
                id=f"arrow_{anchor.id}",
                start=label_attach,
                end=center,
                style=ArrowStyle.LEADER,
                label_id=label.id,
                anchor_id=anchor.id,
            )
            placed_arrows.append(arrow)
            self._log.info(
                "ARROW_DRAWN id=%s style=%s", arrow.id, arrow.style.value
            )

        return LayoutResult(
            labels=placed_labels, arrows=placed_arrows, layout_mode=effective
        )

    def _choose_mode(self, count: int) -> LayoutMode:
        if count <= 2:
            return LayoutMode.RIGHT
        if count <= 4:
            return LayoutMode.RADIAL
        return LayoutMode.RADIAL

    def _resolve_anchor_point(self, anchor: Anchor, illustration_rect: Rect) -> Point:
        c = anchor.center
        if 0.0 <= c.x <= 1.0 and 0.0 <= c.y <= 1.0:
            return Point(
                illustration_rect.x + c.x * illustration_rect.width,
                illustration_rect.y + c.y * illustration_rect.height,
            )
        # Absolute coords assumed relative to illustration top-left if small,
        # otherwise absolute canvas — prefer illustration-relative if within image size-ish
        return Point(
            illustration_rect.x + c.x
            if c.x <= illustration_rect.width
            else c.x,
            illustration_rect.y + c.y
            if c.y <= illustration_rect.height
            else c.y,
        )

    def _candidate_positions(
        self,
        mode: LayoutMode,
        index: int,
        total: int,
        center: Point,
        illust: Rect,
        content: Rect,
    ) -> list[Point]:
        gap = 28.0
        candidates: list[Point] = []

        if mode == LayoutMode.RIGHT:
            candidates.append(Point(illust.right + gap, center.y - 10))
            candidates.append(Point(illust.right + gap, content.y + 40 + index * 40))
        elif mode == LayoutMode.LEFT:
            candidates.append(Point(illust.left - gap - 140, center.y - 10))
            candidates.append(Point(content.x, content.y + 40 + index * 40))
        elif mode == LayoutMode.TOP:
            candidates.append(Point(center.x - 60, illust.top - gap - 30))
            candidates.append(Point(content.x + index * 160, content.y))
        elif mode == LayoutMode.BOTTOM:
            candidates.append(Point(center.x - 60, illust.bottom + gap))
            candidates.append(Point(content.x + index * 160, illust.bottom + gap))
        else:  # RADIAL / fallback
            angle = (2 * math.pi * index / max(total, 1)) - math.pi / 2
            radius = max(illust.width, illust.height) * 0.55 + 40
            cx, cy = illust.center.x, illust.center.y
            candidates.append(
                Point(cx + radius * math.cos(angle) - 60, cy + radius * math.sin(angle) - 10)
            )
            # Cardinal fallbacks
            candidates.extend(
                [
                    Point(illust.right + gap, center.y - 10),
                    Point(illust.left - gap - 140, center.y - 10),
                    Point(center.x - 60, illust.top - gap - 30),
                    Point(center.x - 60, illust.bottom + gap),
                ]
            )

        return candidates

    def _place_without_overlap(
        self,
        prototype: Rect,
        candidates: Sequence[Point],
        occupied: Sequence[Rect],
        content: Rect,
    ) -> Rect:
        for top_left in candidates:
            trial = Rect(top_left.x, top_left.y, prototype.width, prototype.height)
            trial = trial.clamp_inside(content)
            if any(trial.intersects(o) for o in occupied):
                continue
            # Ensure fully inside content
            if (
                trial.left >= content.left
                and trial.top >= content.top
                and trial.right <= content.right
                and trial.bottom <= content.bottom
            ):
                return trial

        # Last resort: clamp first candidate
        first = candidates[0] if candidates else Point(content.x, content.y)
        return Rect(first.x, first.y, prototype.width, prototype.height).clamp_inside(
            content
        )

    def _nearest_edge_point(self, bounds: Rect, target: Point) -> Point:
        # Pick midpoint of the edge facing the target
        cx, cy = bounds.center.x, bounds.center.y
        dx = target.x - cx
        dy = target.y - cy
        if abs(dx) > abs(dy):
            if dx > 0:
                return Point(bounds.right, cy)
            return Point(bounds.left, cy)
        if dy > 0:
            return Point(cx, bounds.bottom)
        return Point(cx, bounds.top)
