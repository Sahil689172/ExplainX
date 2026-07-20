"""Render canvas for frame composition."""

from __future__ import annotations

from PIL import Image

from video_renderer.renderer_config import RendererConfig


class FrameCanvas:
    """RGBA canvas backing store for one frame."""

    def __init__(self, config: RendererConfig | None = None) -> None:
        self.config = config or RendererConfig()
        self.image = Image.new(
            "RGBA",
            (self.config.width, self.config.height),
            self.config.background,
        )

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    def clear(self) -> None:
        self.image = Image.new(
            "RGBA",
            (self.config.width, self.config.height),
            self.config.background,
        )

    def resize(self, width: int, height: int) -> Image.Image:
        return self.image.resize((width, height), Image.Resampling.LANCZOS)

    def crop(self, box: tuple[int, int, int, int]) -> Image.Image:
        return self.image.crop(box)
