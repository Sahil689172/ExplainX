"""Minimal SVG writer (stdlib only) — no svgwrite dependency required.

Produces valid SVG that AssetValidator can parse with lxml. API is intentionally
small and mirrors the subset previously used via svgwrite.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


class SvgDrawing:
    """Accumulate SVG elements and write them to disk."""

    def __init__(self, path: str | Path, *, size: tuple[str, str]) -> None:
        self.path = Path(path)
        self.width, self.height = size
        self._parts: list[str] = []

    def rect(
        self,
        *,
        insert: tuple[float, float],
        size: tuple[float, float],
        fill: str = "#000000",
        stroke: str | None = None,
        stroke_width: float | None = None,
        rx: float | None = None,
        ry: float | None = None,
    ) -> str:
        x, y = insert
        w, h = size
        attrs = [
            f'x="{x}"',
            f'y="{y}"',
            f'width="{w}"',
            f'height="{h}"',
            f'fill="{fill}"',
        ]
        if stroke:
            attrs.append(f'stroke="{stroke}"')
        if stroke_width is not None:
            attrs.append(f'stroke-width="{stroke_width}"')
        if rx is not None:
            attrs.append(f'rx="{rx}"')
        if ry is not None:
            attrs.append(f'ry="{ry}"')
        el = f"<rect {' '.join(attrs)} />"
        self._parts.append(el)
        return el

    def circle(self, *, center: tuple[float, float], r: float, fill: str = "#000000") -> str:
        cx, cy = center
        el = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" />'
        self._parts.append(el)
        return el

    def line(
        self,
        *,
        start: tuple[float, float],
        end: tuple[float, float],
        stroke: str = "#000000",
        stroke_width: float = 1,
    ) -> str:
        x1, y1 = start
        x2, y2 = end
        el = (
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" />'
        )
        self._parts.append(el)
        return el

    def text(
        self,
        content: str,
        *,
        insert: tuple[float, float],
        fill: str = "#000000",
        font_size: float = 14,
    ) -> str:
        x, y = insert
        el = (
            f'<text x="{x}" y="{y}" fill="{fill}" font-size="{font_size}" '
            f'font-family="Arial, Helvetica, sans-serif">'
            f"{escape(content)}</text>"
        )
        self._parts.append(el)
        return el

    def add(self, element: str) -> None:
        """Accept pre-built element strings (from rect/circle/line/text)."""
        if element and element not in self._parts:
            self._parts.append(element)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = "\n  ".join(self._parts)
        svg = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width.replace("px", "")} '
            f'{self.height.replace("px", "")}">\n  {body}\n</svg>\n'
        )
        self.path.write_text(svg, encoding="utf-8")


def drawing(path: str | Path, *, width: int, height: int) -> SvgDrawing:
    """Create a drawing sized in CSS pixels."""
    return SvgDrawing(path, size=(f"{width}px", f"{height}px"))
