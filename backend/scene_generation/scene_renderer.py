"""Scene renderer — abstract backend with Pillow PNG and SVG export."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw

from image_generation.diagram_composer.canvas import fit_image_in_rect, load_illustration
from image_generation.diagram_composer.label_engine import get_draw_font
from image_generation.logger import get_engine_logger
from scene_generation.scene_metadata import (
    ComponentType,
    PlacedComponent,
    SceneMetadata,
    SceneSpec,
)


class SceneExportFormat(str, Enum):
    PNG = "png"
    SVG = "svg"
    JSON = "json"


@dataclass(slots=True)
class SceneRenderContext:
    spec: SceneSpec
    placed: Sequence[PlacedComponent]
    metadata: SceneMetadata


class SceneRenderingBackend(ABC):
    """Abstract scene renderer — swap Pillow / Skia / Cairo later."""

    @abstractmethod
    def render(self, ctx: SceneRenderContext) -> bytes | str:
        ...


class PillowSceneRenderer(SceneRenderingBackend):
    """Raster scene export via Pillow."""

    def render(self, ctx: SceneRenderContext) -> bytes:
        spec = ctx.spec
        img = Image.new("RGBA", (spec.width, spec.height), (255, 255, 252, 255))
        draw = ImageDraw.Draw(img)

        for item in sorted(ctx.placed, key=lambda p: p.component.z_index):
            comp = item.component
            b = item.bounds
            if comp.component_type == ComponentType.BACKGROUND:
                draw.rectangle((0, 0, spec.width, spec.height), fill=(255, 255, 252, 255))
                continue
            if comp.component_type == ComponentType.TITLE:
                draw.text(
                    (b.x, b.y),
                    comp.content,
                    font=get_draw_font(32, bold=True),
                    fill=(20, 40, 70, 255),
                )
                continue
            if comp.component_type == ComponentType.SUBTITLE:
                draw.text(
                    (b.x, b.y),
                    comp.content,
                    font=get_draw_font(18, italic=True),
                    fill=(70, 90, 110, 255),
                )
                continue
            if comp.component_type in (ComponentType.ASSET, ComponentType.DIAGRAM):
                if comp.image_path and Path(comp.image_path).is_file():
                    illustration = load_illustration(comp.image_path)
                    fitted, rect = fit_image_in_rect(illustration, b)
                    img.paste(
                        fitted,
                        (int(rect.x), int(rect.y)),
                        fitted,
                    )
                else:
                    draw.rounded_rectangle(
                        b.as_xyxy_tuple(),
                        radius=8,
                        fill=(230, 238, 248, 255),
                        outline=(80, 120, 160, 255),
                    )
                continue
            if comp.component_type == ComponentType.BULLET_LIST:
                y = b.y
                for bullet in comp.bullets:
                    draw.text((b.x + 8, y), f"• {bullet}", font=get_draw_font(16), fill=(30, 50, 70, 255))
                    y += 24
                continue
            if comp.component_type == ComponentType.LEGEND:
                draw.rounded_rectangle(
                    b.as_xyxy_tuple(),
                    radius=6,
                    fill=(245, 248, 250, 240),
                    outline=(100, 120, 140, 255),
                )
                draw.text((b.x + 8, b.y + 6), "Legend", font=get_draw_font(12, bold=True), fill=(30, 50, 70, 255))
                continue
            if comp.component_type == ComponentType.CAPTION:
                draw.text((b.x, b.y), comp.content, font=get_draw_font(13), fill=(90, 100, 110, 255))
                continue
            if comp.component_type == ComponentType.FOOTER:
                draw.text((b.x, b.y), comp.content, font=get_draw_font(11), fill=(120, 130, 140, 255))
                continue

        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


class SvgSceneRenderer(SceneRenderingBackend):
    """Vector scene export via SVG primitives."""

    def render(self, ctx: SceneRenderContext) -> str:
        spec = ctx.spec
        ns = "http://www.w3.org/2000/svg"
        ET.register_namespace("", ns)
        root = ET.Element(
            "svg",
            {
                "xmlns": ns,
                "width": str(spec.width),
                "height": str(spec.height),
                "viewBox": f"0 0 {spec.width} {spec.height}",
            },
        )
        ET.SubElement(
            root,
            "rect",
            {"width": str(spec.width), "height": str(spec.height), "fill": "#fffdfc"},
        )
        for item in sorted(ctx.placed, key=lambda p: p.component.z_index):
            comp = item.component
            b = item.bounds
            g = ET.SubElement(root, "g", {"id": comp.component_id})
            if comp.component_type == ComponentType.TITLE:
                ET.SubElement(
                    g,
                    "text",
                    {"x": str(b.x), "y": str(b.y + 28), "font-size": "32", "font-weight": "bold"},
                ).text = comp.content
            elif comp.component_type == ComponentType.SUBTITLE:
                ET.SubElement(
                    g,
                    "text",
                    {"x": str(b.x), "y": str(b.y + 18), "font-size": "18", "font-style": "italic"},
                ).text = comp.content
            elif comp.component_type in (ComponentType.ASSET, ComponentType.DIAGRAM):
                ET.SubElement(
                    g,
                    "rect",
                    {
                        "x": str(b.x),
                        "y": str(b.y),
                        "width": str(b.width),
                        "height": str(b.height),
                        "fill": "#e6eef8",
                        "stroke": "#5078a0",
                        "rx": "8",
                    },
                )
            elif comp.component_type == ComponentType.BULLET_LIST:
                y = b.y + 16
                for bullet in comp.bullets:
                    t = ET.SubElement(g, "text", {"x": str(b.x + 8), "y": str(y), "font-size": "16"})
                    t.text = f"• {bullet}"
                    y += 24
            elif comp.component_type == ComponentType.FOOTER:
                ET.SubElement(
                    g,
                    "text",
                    {"x": str(b.x), "y": str(b.y + 14), "font-size": "11"},
                ).text = comp.content
        return ET.tostring(root, encoding="unicode")


@dataclass(slots=True)
class SceneExportResult:
    png_path: str | None = None
    svg_path: str | None = None
    json_path: str | None = None


class SceneRenderer:
    """Export scenes to PNG, SVG, and JSON."""

    def __init__(
        self,
        *,
        pillow: SceneRenderingBackend | None = None,
        svg: SceneRenderingBackend | None = None,
        logger=None,
    ) -> None:
        self._pillow = pillow or PillowSceneRenderer()
        self._svg = svg or SvgSceneRenderer()
        self._log = logger or get_engine_logger("scene_generation")

    def export(
        self,
        ctx: SceneRenderContext,
        output_dir: str | Path,
        *,
        formats: Sequence[SceneExportFormat] | None = None,
    ) -> SceneExportResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = ctx.metadata.scene_id
        formats = formats or (
            SceneExportFormat.PNG,
            SceneExportFormat.SVG,
            SceneExportFormat.JSON,
        )
        result = SceneExportResult()

        if SceneExportFormat.PNG in formats:
            png_path = out / f"{stem}.png"
            png_path.write_bytes(self._pillow.render(ctx))  # type: ignore[arg-type]
            result.png_path = str(png_path)

        if SceneExportFormat.SVG in formats:
            svg_path = out / f"{stem}.svg"
            svg_path.write_text(self._svg.render(ctx), encoding="utf-8")  # type: ignore[arg-type]
            result.svg_path = str(svg_path)

        if SceneExportFormat.JSON in formats:
            json_path = out / f"{stem}.json"
            json_path.write_text(json.dumps(ctx.metadata.to_dict(), indent=2), encoding="utf-8")
            result.json_path = str(json_path)

        self._log.info(
            "SCENE_RENDERED scene_id=%s png=%s svg=%s json=%s",
            stem,
            result.png_path or "-",
            result.svg_path or "-",
            result.json_path or "-",
        )
        return result
