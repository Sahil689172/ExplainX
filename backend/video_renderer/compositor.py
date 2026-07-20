"""Pillow compositor — alpha blend layers with z-ordering."""

from __future__ import annotations

from PIL import Image

from image_generation.logger import get_engine_logger
from video_renderer.renderer_types import CameraState, RenderLayer


class Compositor:
    """Composite transformed RGBA layers onto a canvas."""

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("video_renderer")

    def composite(
        self,
        base: Image.Image,
        layers: list[Image.Image],
        *,
        positions: list[tuple[int, int]],
        opacities: list[float],
    ) -> Image.Image:
        canvas = base.copy()
        for layer_img, (x, y), opacity in zip(layers, positions, opacities):
            if opacity < 0.01:
                continue
            if opacity < 0.999:
                layer_img = self._apply_opacity(layer_img, opacity)
            canvas.paste(layer_img, (x, y), layer_img)
        return canvas

    def composite_layers(
        self,
        canvas: Image.Image,
        rendered: list[tuple[RenderLayer, Image.Image]],
        *,
        camera: CameraState,
    ) -> Image.Image:
        sorted_items = sorted(rendered, key=lambda item: item[0].z_index)
        for layer, img in sorted_items:
            x = int(layer.transform.position[0])
            y = int(layer.transform.position[1])
            opacity = layer.transform.opacity
            if opacity < 0.01:
                continue
            if opacity < 0.999:
                img = self._apply_opacity(img, opacity)
            if abs(layer.transform.rotation) > 0.01:
                img = img.rotate(-layer.transform.rotation, expand=True, resample=Image.Resampling.BICUBIC)
            sx, sy = layer.transform.scale
            if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
                nw = max(1, int(img.width * sx))
                nh = max(1, int(img.height * sy))
                img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            # Apply camera pan offset to layer positions
            px = x + int(camera.pan[0] * 0.25)
            py = y + int(camera.pan[1] * 0.25)
            canvas.paste(img, (px, py), img)
            self._log.info("LAYER_RENDERED id=%s x=%s y=%s opacity=%.2f", layer.layer_id, px, py, opacity)
        return canvas

    @staticmethod
    def _apply_opacity(image: Image.Image, opacity: float) -> Image.Image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        r, g, b, a = image.split()
        a = a.point(lambda p: int(p * opacity))
        return Image.merge("RGBA", (r, g, b, a))
