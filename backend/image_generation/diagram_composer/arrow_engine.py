"""Arrow engine — geometric paths for leaders and flow arrows."""

from __future__ import annotations

import math
from dataclasses import dataclass

from image_generation.diagram_composer.elements import ArrowStyle, PlacedArrow
from image_generation.diagram_composer.geometry import (
    Point,
    perpendicular,
    quadratic_bezier,
    unit_vector,
)


@dataclass(slots=True)
class ArrowPath:
    """Renderable polyline (and optional second head) for an arrow."""

    points: list[Point]
    head_at_end: bool = True
    head_at_start: bool = False
    dashed: bool = False
    style: ArrowStyle = ArrowStyle.STRAIGHT


class ArrowEngine:
    """Build arrow geometry from placed arrow descriptors."""

    def build(self, arrow: PlacedArrow, *, curve_bulge: float = 0.25) -> ArrowPath:
        style = arrow.style
        dashed = arrow.dashed or style == ArrowStyle.DASHED
        double = arrow.double_headed or style == ArrowStyle.DOUBLE

        if style in (ArrowStyle.CURVED,) or arrow.control is not None:
            control = arrow.control or self._auto_control(
                arrow.start, arrow.end, bulge=curve_bulge
            )
            points = quadratic_bezier(arrow.start, control, arrow.end)
            return ArrowPath(
                points=points,
                head_at_end=True,
                head_at_start=double,
                dashed=dashed,
                style=ArrowStyle.CURVED,
            )

        # Straight / leader / dashed / double
        return ArrowPath(
            points=[arrow.start, arrow.end],
            head_at_end=True,
            head_at_start=double,
            dashed=dashed,
            style=style,
        )

    def arrow_head(
        self, tip: Point, toward: Point, *, size: float = 10.0
    ) -> tuple[Point, Point, Point]:
        """Return three points of a triangular arrow head at tip, pointing along toward→tip."""
        direction = unit_vector(toward, tip)
        # Base center sits size pixels back from tip
        base = Point(tip.x - direction.x * size, tip.y - direction.y * size)
        perp = perpendicular(direction)
        left = Point(base.x + perp.x * size * 0.55, base.y + perp.y * size * 0.55)
        right = Point(base.x - perp.x * size * 0.55, base.y - perp.y * size * 0.55)
        return (tip, left, right)

    def _auto_control(self, start: Point, end: Point, *, bulge: float) -> Point:
        mid = Point((start.x + end.x) / 2, (start.y + end.y) / 2)
        direction = unit_vector(start, end)
        perp = perpendicular(direction)
        dist = start.distance_to(end)
        return Point(mid.x + perp.x * dist * bulge, mid.y + perp.y * dist * bulge)

    def make_flow_arrow(
        self,
        start: Point,
        end: Point,
        *,
        arrow_id: str,
        curved: bool = False,
        dashed: bool = False,
        double: bool = False,
    ) -> PlacedArrow:
        style = ArrowStyle.STRAIGHT
        if dashed:
            style = ArrowStyle.DASHED
        if curved:
            style = ArrowStyle.CURVED
        if double:
            style = ArrowStyle.DOUBLE
        return PlacedArrow(
            id=arrow_id,
            start=start,
            end=end,
            style=style,
            control=self._auto_control(start, end, bulge=0.3) if curved else None,
            double_headed=double,
            dashed=dashed,
        )
