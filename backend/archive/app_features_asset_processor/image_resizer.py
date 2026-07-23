"""Fit images inside a square TARGET_SIZE without stretching."""

from __future__ import annotations

from PIL import Image


class ImageResizer:
    """Contain-fit resize into ``target_size`` × ``target_size``."""

    def __init__(self, target_size: int = 512) -> None:
        if target_size < 8:
            raise ValueError("target_size must be >= 8")
        self.target_size = int(target_size)

    def resize(self, image: Image.Image) -> Image.Image:
        """Scale so max(width, height) <= target_size; never upscale by default."""
        w, h = image.size
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid image size: {w}x{h}")

        longest = max(w, h)
        if longest <= self.target_size:
            return image.copy()

        scale = self.target_size / float(longest)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        return image.resize((new_w, new_h), Image.Resampling.LANCZOS)
