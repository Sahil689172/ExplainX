"""Normalize images to clean RGBA (EXIF, profiles, formats)."""

from __future__ import annotations

from PIL import Image, ImageOps


class ImageNormalizer:
    """Convert every image to a clean RGBA canvas."""

    def normalize(self, image: Image.Image) -> Image.Image:
        """Fix orientation, drop profiles, convert to RGBA, preserve alpha."""
        oriented = ImageOps.exif_transpose(image)
        rgba = oriented.convert("RGBA")
        # Rebuild without ICC / EXIF baggage.
        clean = Image.new("RGBA", rgba.size)
        clean.paste(rgba)
        return clean
