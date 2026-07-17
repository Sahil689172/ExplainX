"""Sprite — an image object placed in a scene."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.features.renderer.objects.transform import Transform


@dataclass(slots=True)
class Sprite:
    """One drawable object with transform and draw order."""

    id: str
    image_path: Path
    transform: Transform
    z_index: int = 0

    def load_rgba(self):  # noqa: ANN201 — returns PIL.Image.Image
        """Load the sprite image as RGBA (Pillow)."""
        from PIL import Image

        if not self.image_path.is_file():
            raise FileNotFoundError(f"Sprite image not found: {self.image_path}")
        return Image.open(self.image_path).convert("RGBA")

    def apply_transform(self, image):  # noqa: ANN001, ANN201
        """Return a new RGBA image with scale, rotation, and opacity applied."""
        from PIL import Image

        tf = self.transform
        if not tf.visible or tf.opacity <= 0.0:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        out = image
        if tf.scale != 1.0:
            w = max(1, int(round(out.width * tf.scale)))
            h = max(1, int(round(out.height * tf.scale)))
            out = out.resize((w, h), Image.Resampling.LANCZOS)

        if abs(tf.rotation) > 1e-6:
            # Pillow rotate is counter-clockwise; treat manifest rotation as clockwise.
            out = out.rotate(-tf.rotation, expand=True, resample=Image.Resampling.BICUBIC)

        if tf.opacity < 1.0:
            alpha = out.getchannel("A")
            alpha = alpha.point(lambda p: int(p * tf.opacity))
            out.putalpha(alpha)

        return out
