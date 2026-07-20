"""Label engine — font metrics, wrapping, and text measurement."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from PIL import ImageDraw, ImageFont

from image_generation.diagram_composer.geometry import Point, Rect


@dataclass(slots=True)
class LabelStyle:
    font_size: int = 14
    bold: bool = False
    italic: bool = False
    max_width: int = 160
    line_spacing: float = 1.2


class LabelEngine:
    """Prepare multi-line educational labels with auto-wrap."""

    def __init__(self, default_style: LabelStyle | None = None) -> None:
        self.default_style = default_style or LabelStyle()

    def wrap(self, text: str, *, max_width: int | None = None, font_size: int | None = None) -> list[str]:
        style = self.default_style
        width = max_width or style.max_width
        size = font_size or style.font_size
        font = _load_font(size, bold=style.bold, italic=style.italic)
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if _text_width(font, candidate) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def measure(
        self,
        lines: Sequence[str],
        *,
        font_size: int | None = None,
        bold: bool = False,
        italic: bool = False,
        padding: int = 6,
    ) -> tuple[float, float]:
        size = font_size or self.default_style.font_size
        font = _load_font(size, bold=bold, italic=italic)
        if not lines:
            return (float(padding * 2), float(size + padding * 2))
        widths = [_text_width(font, line) for line in lines]
        line_h = size * self.default_style.line_spacing
        height = line_h * len(lines) + padding * 2
        width = max(widths) + padding * 2
        return (float(width), float(height))

    def make_bounds(
        self,
        text: str,
        top_left: Point,
        *,
        style: LabelStyle | None = None,
    ) -> tuple[list[str], Rect]:
        style = style or self.default_style
        lines = self.wrap(text, max_width=style.max_width, font_size=style.font_size)
        w, h = self.measure(
            lines, font_size=style.font_size, bold=style.bold, italic=style.italic
        )
        return lines, Rect(top_left.x, top_left.y, w, h)


@lru_cache(maxsize=32)
def _load_font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
    candidates: list[str] = []
    if bold and italic:
        candidates += ["arialbi.ttf", "DejaVuSans-BoldOblique.ttf"]
    elif bold:
        candidates += ["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]
    elif italic:
        candidates += ["ariali.ttf", "DejaVuSans-Oblique.ttf"]
    else:
        candidates += ["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_width(font: ImageFont.ImageFont, text: str) -> float:
    # Pillow >= 8: getbbox / getlength
    if hasattr(font, "getlength"):
        try:
            return float(font.getlength(text))
        except Exception:
            pass
    bbox = font.getbbox(text) if hasattr(font, "getbbox") else (0, 0, len(text) * 6, 10)
    return float(bbox[2] - bbox[0])


def get_draw_font(size: int = 14, *, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
    """Public helper for renderers."""
    return _load_font(size, bold=bold, italic=italic)


def draw_multiline_text(
    draw: ImageDraw.ImageDraw,
    position: Point,
    lines: Sequence[str],
    *,
    fill: tuple[int, int, int, int],
    font_size: int = 14,
    bold: bool = False,
    italic: bool = False,
    line_spacing: float = 1.2,
) -> None:
    font = _load_font(font_size, bold=bold, italic=italic)
    y = position.y
    for line in lines:
        draw.text((position.x, y), line, font=font, fill=fill)
        y += font_size * line_spacing
