"""Render individual layers to RGBA images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from image_generation.diagram_composer.canvas import fit_image_in_rect, load_illustration
from image_generation.diagram_composer.geometry import Rect
from image_generation.diagram_composer.label_engine import get_draw_font
from image_generation.logger import get_engine_logger
from video_renderer.renderer_config import RendererConfig
from video_renderer.renderer_types import LayerType, RenderLayer


class FrameRenderer:
    """Render a single layer to an RGBA PIL image (Pillow backend)."""

    def __init__(self, *, config: RendererConfig | None = None, logger=None) -> None:
        self._config = config or RendererConfig()
        self._log = logger or get_engine_logger("video_renderer")

    def render_layer(self, layer: RenderLayer) -> Image.Image:
        if layer.layer_type == LayerType.BACKGROUND:
            return Image.new(
                "RGBA",
                (self._config.width, self._config.height),
                self._config.background,
            )

        if layer.layer_type in (LayerType.ASSET, LayerType.DIAGRAM):
            return self._render_image_layer(layer)

        if layer.layer_type == LayerType.BULLETS:
            return self._render_bullets(layer)

        if layer.layer_type == LayerType.LEGEND:
            return self._render_legend(layer)

        return self._render_text(layer)

    def _render_image_layer(self, layer: RenderLayer) -> Image.Image:
        bx, by, bw, bh = layer.bounds
        rect = Rect(bx, by, bw, bh)
        if layer.image_path and Path(layer.image_path).is_file():
            illustration = load_illustration(layer.image_path)
            fitted, fit_rect = fit_image_in_rect(illustration, rect)
            out = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
            out.paste(fitted, (int(fit_rect.x - bx), int(fit_rect.y - by)), fitted)
            return out
        out = Image.new("RGBA", (max(1, int(bw)), max(1, int(bh))), (230, 238, 248, 255))
        draw = ImageDraw.Draw(out)
        draw.rounded_rectangle((0, 0, int(bw), int(bh)), radius=8, outline=(80, 120, 160, 255))
        return out

    def _render_text(self, layer: RenderLayer) -> Image.Image:
        bx, by, bw, bh = layer.bounds
        out = Image.new("RGBA", (max(1, int(bw)), max(1, int(bh))), (0, 0, 0, 0))
        draw = ImageDraw.Draw(out)
        if layer.layer_type == LayerType.TITLE:
            font = get_draw_font(32, bold=True)
            fill = (20, 40, 70, 255)
        elif layer.layer_type == LayerType.SUBTITLE:
            font = get_draw_font(18, italic=True)
            fill = (70, 90, 110, 255)
        elif layer.layer_type == LayerType.FOOTER:
            font = get_draw_font(11)
            fill = (120, 130, 140, 255)
        else:
            font = get_draw_font(14)
            fill = (30, 50, 70, 255)
        draw.text((0, 0), layer.content, font=font, fill=fill)
        return out

    def _render_bullets(self, layer: RenderLayer) -> Image.Image:
        bx, by, bw, bh = layer.bounds
        out = Image.new("RGBA", (max(1, int(bw)), max(1, int(bh))), (0, 0, 0, 0))
        draw = ImageDraw.Draw(out)
        y = 0
        for bullet in layer.bullets:
            draw.text((8, y), f"• {bullet}", font=get_draw_font(16), fill=(30, 50, 70, 255))
            y += 24
        return out

    def _render_legend(self, layer: RenderLayer) -> Image.Image:
        bx, by, bw, bh = layer.bounds
        out = Image.new("RGBA", (max(1, int(bw)), max(1, int(bh))), (0, 0, 0, 0))
        draw = ImageDraw.Draw(out)
        draw.rounded_rectangle((0, 0, int(bw), int(bh)), radius=6, fill=(245, 248, 250, 240), outline=(100, 120, 140, 255))
        draw.text((8, 6), layer.content or "Legend", font=get_draw_font(12, bold=True), fill=(30, 50, 70, 255))
        return out
