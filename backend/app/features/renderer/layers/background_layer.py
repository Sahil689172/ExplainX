"""Background layer — base canvas for a scene."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class BackgroundLayer:
    """Full-frame background image."""

    image_path: Path
    label: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.image_path.name

    def render(self):  # noqa: ANN201 — returns PIL.Image.Image
        """Load the background as an RGBA canvas."""
        from PIL import Image

        if not self.image_path.is_file():
            raise FileNotFoundError(f"Background image not found: {self.image_path}")
        return Image.open(self.image_path).convert("RGBA")
