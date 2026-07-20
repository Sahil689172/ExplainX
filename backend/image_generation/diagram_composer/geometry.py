"""2D geometry primitives for diagram composition."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class Point:
    """A 2D point in canvas coordinates (pixels, origin top-left)."""

    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def as_int_tuple(self) -> tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))

    def offset(self, dx: float, dy: float) -> Point:
        return Point(self.x + dx, self.y + dy)

    def distance_to(self, other: Point) -> float:
        return math.hypot(other.x - self.x, other.y - self.y)


@dataclass(slots=True)
class Rect:
    """Axis-aligned rectangle."""

    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    def contains_point(self, p: Point) -> bool:
        return self.left <= p.x <= self.right and self.top <= p.y <= self.bottom

    def intersects(self, other: Rect) -> bool:
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bottom < other.top
            or self.top > other.bottom
        )

    def inflate(self, pad: float) -> Rect:
        return Rect(
            self.x - pad,
            self.y - pad,
            self.width + 2 * pad,
            self.height + 2 * pad,
        )

    def clamp_inside(self, bounds: Rect) -> Rect:
        """Shift this rect so it fits inside bounds (may still clip if too large)."""
        x = min(max(self.x, bounds.left), max(bounds.left, bounds.right - self.width))
        y = min(max(self.y, bounds.top), max(bounds.top, bounds.bottom - self.height))
        return Rect(x, y, self.width, self.height)

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)

    def as_xyxy_tuple(self) -> tuple[int, int, int, int]:
        """Pillow box: (left, top, right, bottom)."""
        return (
            int(round(self.left)),
            int(round(self.top)),
            int(round(self.right)),
            int(round(self.bottom)),
        )


@dataclass(slots=True)
class BoundingBox:
    """Object bounding box — often normalized 0–1 relative to illustration."""

    x: float
    y: float
    width: float
    height: float
    normalized: bool = False

    def to_rect(self, *, canvas_width: float, canvas_height: float) -> Rect:
        if self.normalized:
            return Rect(
                self.x * canvas_width,
                self.y * canvas_height,
                self.width * canvas_width,
                self.height * canvas_height,
            )
        return Rect(self.x, self.y, self.width, self.height)

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)


def lerp(a: Point, b: Point, t: float) -> Point:
    return Point(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)


def unit_vector(from_p: Point, to_p: Point) -> Point:
    dx = to_p.x - from_p.x
    dy = to_p.y - from_p.y
    length = math.hypot(dx, dy) or 1.0
    return Point(dx / length, dy / length)


def perpendicular(v: Point) -> Point:
    return Point(-v.y, v.x)


def quadratic_bezier(p0: Point, p1: Point, p2: Point, steps: int = 24) -> list[Point]:
    pts: list[Point] = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * p1.x + t**2 * p2.x
        y = (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * p1.y + t**2 * p2.y
        pts.append(Point(x, y))
    return pts
