"""Contain-fit resize into a square TARGET_SIZE canvas with transparent padding."""

from __future__ import annotations

from PIL import Image


class ImageResizer:
    """Fit image inside ``target_size``×``target_size`` without stretching.

    Aspect ratio is preserved. The object is centered on a transparent canvas.
    """

    def __init__(self, target_size: int = 512) -> None:
        if target_size < 8:
            raise ValueError("target_size must be >= 8")
        self.target_size = int(target_size)

    def resize(self, image: Image.Image) -> Image.Image:
        rgba = image.convert("RGBA")
        w, h = rgba.size
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid image size: {w}x{h}")

        scale = min(self.target_size / float(w), self.target_size / float(h))
        # Never upscale beyond original for quality; still pad to canvas.
        # Spec: fit inside target — allow downscale; if already smaller, keep size.
        if scale > 1.0:
            scale = 1.0

        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        if (new_w, new_h) != (w, h):
            # Bilinear (Pillow BILINEAR) for smooth downscale.
            fitted = rgba.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            fitted = rgba

        canvas = Image.new("RGBA", (self.target_size, self.target_size), (0, 0, 0, 0))
        offset_x = (self.target_size - new_w) // 2
        offset_y = (self.target_size - new_h) // 2
        canvas.paste(fitted, (offset_x, offset_y), fitted)
        return canvas
