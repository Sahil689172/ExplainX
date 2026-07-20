"""Canvas model for educational diagram composition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image

from image_generation.diagram_composer.geometry import Rect


class BackgroundMode(str, Enum):
    TRANSPARENT = "transparent"
    WHITE = "white"
    THEMED = "themed"


@dataclass(slots=True)
class Canvas:
    """Logical diagram canvas with content area and margins."""

    width: int
    height: int
    padding: int = 48
    margin: int = 24
    background_mode: BackgroundMode = BackgroundMode.WHITE

    @property
    def bounds(self) -> Rect:
        return Rect(0, 0, float(self.width), float(self.height))

    @property
    def content_bounds(self) -> Rect:
        m = self.margin + self.padding
        return Rect(
            float(m),
            float(m),
            float(self.width - 2 * m),
            float(self.height - 2 * m),
        )

    @property
    def illustration_bounds(self) -> Rect:
        """Central region reserved for the source illustration."""
        content = self.content_bounds
        # Leave side gutters for labels (~22% each side on wide canvases)
        side = max(120.0, content.width * 0.18)
        top = max(80.0, content.height * 0.12)
        bottom = max(100.0, content.height * 0.16)
        return Rect(
            content.x + side,
            content.y + top,
            max(64.0, content.width - 2 * side),
            max(64.0, content.height - top - bottom),
        )

    def auto_resize_for_image(
        self, image_size: tuple[int, int], *, min_side: int = 640
    ) -> Canvas:
        """Return a new canvas sized to fit the illustration comfortably."""
        iw, ih = image_size
        target_w = max(min_side, int(iw * 1.6) + 2 * (self.padding + self.margin))
        target_h = max(min_side, int(ih * 1.5) + 2 * (self.padding + self.margin) + 80)
        return Canvas(
            width=target_w,
            height=target_h,
            padding=self.padding,
            margin=self.margin,
            background_mode=self.background_mode,
        )


def load_illustration(path: str | Path) -> Image.Image:
    """Load an illustration as RGBA."""
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def fit_image_in_rect(image: Image.Image, rect: Rect) -> tuple[Image.Image, Rect]:
    """Scale image to fit inside rect preserving aspect; return image + draw rect."""
    if image.width <= 0 or image.height <= 0:
        return image, rect
    scale = min(rect.width / image.width, rect.height / image.height)
    nw = max(1, int(image.width * scale))
    nh = max(1, int(image.height * scale))
    resized = image.resize((nw, nh), Image.Resampling.LANCZOS)
    x = rect.x + (rect.width - nw) / 2
    y = rect.y + (rect.height - nh) / 2
    return resized, Rect(x, y, float(nw), float(nh))
