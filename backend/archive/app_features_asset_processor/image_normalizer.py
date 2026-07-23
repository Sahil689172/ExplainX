"""Normalize images to clean RGBA without EXIF/profile quirks."""

from __future__ import annotations

from PIL import Image, ImageOps


class ImageNormalizer:
    """Convert to RGBA, fix orientation, drop embedded color profiles."""

    def normalize(self, image: Image.Image) -> Image.Image:
        # Apply EXIF orientation before stripping metadata.
        oriented = ImageOps.exif_transpose(image)
        rgba = oriented.convert("RGBA")

        # Rebuild pixels without ICC / EXIF baggage.
        clean = Image.new("RGBA", rgba.size)
        clean.paste(rgba)
        return clean
