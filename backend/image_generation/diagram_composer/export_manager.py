"""Export manager and rendering backends (Pillow raster + SVG vector)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw

from image_generation.diagram_composer.arrow_engine import ArrowEngine
from image_generation.diagram_composer.canvas import Canvas
from image_generation.diagram_composer.geometry import Rect
from image_generation.diagram_composer.elements import (
    DiagramMetadata,
    LegendBlock,
    PlacedArrow,
    PlacedLabel,
)
from image_generation.diagram_composer.label_engine import draw_multiline_text, get_draw_font
from image_generation.diagram_composer.theme_manager import ThemeColors
from image_generation.logger import get_engine_logger


class ExportFormat(str, Enum):
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"  # future
    PPTX = "pptx"  # future


@dataclass(slots=True)
class RenderContext:
    """Everything a renderer needs for one diagram pass."""

    canvas: Canvas
    illustration: Image.Image
    illustration_rect: Rect
    labels: Sequence[PlacedLabel]
    arrows: Sequence[PlacedArrow]
    legend: LegendBlock | None
    theme: ThemeColors
    title: str | None = None
    subtitle: str | None = None
    caption: str | None = None


class RenderingBackend(ABC):
    """Abstract rendering backend — swap Pillow / Cairo / Skia later."""

    @abstractmethod
    def render(self, ctx: RenderContext) -> bytes | str:
        """Return PNG bytes or SVG string."""


class PillowRenderer(RenderingBackend):
    """Raster rendering via Pillow."""

    def __init__(self, arrow_engine: ArrowEngine | None = None) -> None:
        self._arrows = arrow_engine or ArrowEngine()

    def render(self, ctx: RenderContext) -> bytes:
        canvas = ctx.canvas
        theme = ctx.theme
        bg = (0, 0, 0, 0) if canvas.background_mode.value == "transparent" else theme.background
        img = Image.new("RGBA", (canvas.width, canvas.height), bg)
        draw = ImageDraw.Draw(img)

        # Title / subtitle
        y_cursor = canvas.margin
        if ctx.title:
            title_font = get_draw_font(22, bold=True)
            draw.text((canvas.margin, y_cursor), ctx.title, font=title_font, fill=theme.title)
            y_cursor += 28
        if ctx.subtitle:
            sub_font = get_draw_font(14, italic=True)
            draw.text((canvas.margin, y_cursor), ctx.subtitle, font=sub_font, fill=theme.muted_text)
            y_cursor += 22

        # Illustration
        illust_rect = ctx.illustration_rect
        img.paste(
            ctx.illustration,
            (int(illust_rect.x), int(illust_rect.y)),
            ctx.illustration,
        )

        # Arrows under labels
        for arrow in ctx.arrows:
            self._draw_arrow(draw, arrow, theme)

        # Labels
        for label in ctx.labels:
            b = label.bounds
            draw.rounded_rectangle(
                b.as_xyxy_tuple(),
                radius=6,
                fill=theme.label_fill,
                outline=theme.stroke,
                width=1,
            )
            draw_multiline_text(
                draw,
                label.position,
                label.lines or [label.text],
                fill=theme.text,
                font_size=label.font_size,
                bold=label.bold,
                italic=label.italic,
            )

        # Legend
        if ctx.legend:
            self._draw_legend(draw, ctx.legend, theme)

        # Caption
        if ctx.caption:
            cap_font = get_draw_font(12)
            draw.text(
                (canvas.margin, canvas.height - canvas.margin - 16),
                ctx.caption,
                font=cap_font,
                fill=theme.muted_text,
            )

        from io import BytesIO

        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _draw_arrow(self, draw: ImageDraw.ImageDraw, arrow: PlacedArrow, theme: ThemeColors) -> None:
        path = self._arrows.build(arrow)
        pts = [p.as_int_tuple() for p in path.points]
        if len(pts) < 2:
            return
        dash = (6, 4) if path.dashed else None
        draw.line(pts, fill=theme.arrow, width=2, joint="curve")
        if path.head_at_end:
            head = self._arrows.arrow_head(path.points[-1], path.points[-2])
            draw.polygon([p.as_int_tuple() for p in head], fill=theme.arrow)
        if path.head_at_start:
            head = self._arrows.arrow_head(path.points[0], path.points[1])
            draw.polygon([p.as_int_tuple() for p in head], fill=theme.arrow)
        _ = dash  # Pillow line dash limited; kept for SVG parity

    def _draw_legend(
        self, draw: ImageDraw.ImageDraw, legend: LegendBlock, theme: ThemeColors
    ) -> None:
        b = legend.bounds
        draw.rounded_rectangle(
            b.as_xyxy_tuple(), radius=8, fill=theme.legend_bg, outline=theme.stroke, width=1
        )
        x = b.x + 10
        y = b.y + 8
        title_font = get_draw_font(12, bold=True)
        draw.text((x, y), legend.title, font=title_font, fill=theme.text)
        y += 18
        for item in legend.items:
            color = item.swatch_color or theme.accent
            if item.symbol == "arrow":
                draw.line([(x, y + 6), (x + 14, y + 6)], fill=color, width=2)
                draw.polygon([(x + 14, y + 6), (x + 10, y + 3), (x + 10, y + 9)], fill=color)
            else:
                draw.ellipse((x, y, x + 12, y + 12), fill=color, outline=theme.stroke)
            text = f"{item.key} = {item.description}"
            draw.text((x + 18, y - 1), text, font=get_draw_font(11), fill=theme.text)
            y += 20


class SvgRenderer(RenderingBackend):
    """Vector rendering via SVG primitives."""

    def __init__(self, arrow_engine: ArrowEngine | None = None) -> None:
        self._arrows = arrow_engine or ArrowEngine()

    def render(self, ctx: RenderContext) -> str:
        canvas = ctx.canvas
        theme = ctx.theme
        ns = "http://www.w3.org/2000/svg"
        ET.register_namespace("", ns)
        root = ET.Element(
            "svg",
            {
                "xmlns": ns,
                "width": str(canvas.width),
                "height": str(canvas.height),
                "viewBox": f"0 0 {canvas.width} {canvas.height}",
            },
        )

        if canvas.background_mode.value != "transparent":
            ET.SubElement(
                root,
                "rect",
                {
                    "width": str(canvas.width),
                    "height": str(canvas.height),
                    "fill": _rgba(theme.background),
                },
            )

        if ctx.title:
            ET.SubElement(
                root,
                "text",
                {
                    "x": str(canvas.margin),
                    "y": str(canvas.margin + 20),
                    "fill": _rgba(theme.title),
                    "font-size": "22",
                    "font-weight": "bold",
                },
            ).text = ctx.title

        if ctx.subtitle:
            ET.SubElement(
                root,
                "text",
                {
                    "x": str(canvas.margin),
                    "y": str(canvas.margin + 44),
                    "fill": _rgba(theme.muted_text),
                    "font-size": "14",
                    "font-style": "italic",
                },
            ).text = ctx.subtitle

        illust = ctx.illustration_rect
        # Embed illustration as embedded PNG data URI would be heavy; use foreignObject placeholder
        # For vector export we draw a rounded rect frame + note — real pipeline can embed href later.
        g_img = ET.SubElement(root, "g", {"id": "illustration"})
        ET.SubElement(
            g_img,
            "rect",
            {
                "x": str(illust.x),
                "y": str(illust.y),
                "width": str(illust.width),
                "height": str(illust.height),
                "fill": "none",
                "stroke": _rgba(theme.stroke),
                "stroke-width": "1",
                "rx": "4",
            },
        )

        g_arrows = ET.SubElement(root, "g", {"id": "arrows"})
        for arrow in ctx.arrows:
            self._svg_arrow(g_arrows, arrow, theme)

        g_labels = ET.SubElement(root, "g", {"id": "labels"})
        for label in ctx.labels:
            b = label.bounds
            ET.SubElement(
                g_labels,
                "rect",
                {
                    "x": str(b.x),
                    "y": str(b.y),
                    "width": str(b.width),
                    "height": str(b.height),
                    "rx": "6",
                    "fill": _rgba(theme.label_fill),
                    "stroke": _rgba(theme.stroke),
                },
            )
            lines = label.lines or [label.text]
            for i, line in enumerate(lines):
                ET.SubElement(
                    g_labels,
                    "text",
                    {
                        "x": str(label.position.x),
                        "y": str(label.position.y + 14 + i * 16),
                        "fill": _rgba(theme.text),
                        "font-size": str(label.font_size),
                    },
                ).text = line

        if ctx.legend:
            self._svg_legend(root, ctx.legend, theme)

        if ctx.caption:
            ET.SubElement(
                root,
                "text",
                {
                    "x": str(canvas.margin),
                    "y": str(canvas.height - canvas.margin),
                    "fill": _rgba(theme.muted_text),
                    "font-size": "12",
                },
            ).text = ctx.caption

        return ET.tostring(root, encoding="unicode")

    def _svg_arrow(self, parent: ET.Element, arrow: PlacedArrow, theme: ThemeColors) -> None:
        path = self._arrows.build(arrow)
        if len(path.points) < 2:
            return
        d = "M " + " L ".join(f"{p.x:.1f} {p.y:.1f}" for p in path.points)
        attrs = {
            "d": d,
            "fill": "none",
            "stroke": _rgba(theme.arrow),
            "stroke-width": "2",
        }
        if path.dashed:
            attrs["stroke-dasharray"] = "6 4"
        ET.SubElement(parent, "path", attrs)
        if path.head_at_end:
            head = self._arrows.arrow_head(path.points[-1], path.points[-2])
            pts = " ".join(f"{p.x:.1f},{p.y:.1f}" for p in head)
            ET.SubElement(parent, "polygon", {"points": pts, "fill": _rgba(theme.arrow)})

    def _svg_legend(self, root: ET.Element, legend: LegendBlock, theme: ThemeColors) -> None:
        b = legend.bounds
        g = ET.SubElement(root, "g", {"id": "legend"})
        ET.SubElement(
            g,
            "rect",
            {
                "x": str(b.x),
                "y": str(b.y),
                "width": str(b.width),
                "height": str(b.height),
                "rx": "8",
                "fill": _rgba(theme.legend_bg),
                "stroke": _rgba(theme.stroke),
            },
        )
        ET.SubElement(
            g,
            "text",
            {
                "x": str(b.x + 10),
                "y": str(b.y + 20),
                "fill": _rgba(theme.text),
                "font-size": "12",
                "font-weight": "bold",
            },
        ).text = legend.title
        y = b.y + 36
        for item in legend.items:
            color = item.swatch_color or theme.accent
            ET.SubElement(
                g,
                "circle",
                {
                    "cx": str(b.x + 16),
                    "cy": str(y),
                    "r": "6",
                    "fill": _rgba(color),
                },
            )
            ET.SubElement(
                g,
                "text",
                {
                    "x": str(b.x + 28),
                    "y": str(y + 4),
                    "fill": _rgba(theme.text),
                    "font-size": "11",
                },
            ).text = f"{item.key} = {item.description}"
            y += 20


def _rgba(color: tuple[int, int, int, int]) -> str:
    r, g, b, a = color
    if a >= 255:
        return f"rgb({r},{g},{b})"
    return f"rgba({r},{g},{b},{a / 255:.3f})"


@dataclass(slots=True)
class ExportResult:
    png_path: str | None = None
    svg_path: str | None = None
    metadata_path: str | None = None


class ExportManager:
    """Write diagram outputs to disk in PNG / SVG (+ metadata JSON)."""

    def __init__(
        self,
        *,
        pillow_renderer: RenderingBackend | None = None,
        svg_renderer: RenderingBackend | None = None,
        logger=None,
    ) -> None:
        self._pillow = pillow_renderer or PillowRenderer()
        self._svg = svg_renderer or SvgRenderer()
        self._log = logger or get_engine_logger("image_generation.diagram_composer")

    def export(
        self,
        ctx: RenderContext,
        metadata: DiagramMetadata,
        output_dir: str | Path,
        *,
        formats: Sequence[ExportFormat] | None = None,
    ) -> ExportResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = metadata.diagram_id
        formats = formats or (ExportFormat.PNG, ExportFormat.SVG)
        result = ExportResult()

        if ExportFormat.PNG in formats:
            png_bytes = self._pillow.render(ctx)
            png_path = out / f"{stem}.png"
            png_path.write_bytes(png_bytes)
            result.png_path = str(png_path)
            self._log.info("EXPORT_COMPLETED format=png path=%s", png_path)

        if ExportFormat.SVG in formats:
            svg_text = self._svg.render(ctx)
            svg_path = out / f"{stem}.svg"
            svg_path.write_text(svg_text, encoding="utf-8")
            result.svg_path = str(svg_path)
            self._log.info("EXPORT_COMPLETED format=svg path=%s", svg_path)

        import json

        meta_path = out / f"{stem}.json"
        meta_path.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
        result.metadata_path = str(meta_path)
        self._log.info("EXPORT_COMPLETED format=metadata path=%s", meta_path)

        return result
