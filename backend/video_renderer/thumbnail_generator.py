"""Thumbnail generation from frame sequences."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

from image_generation.logger import get_engine_logger
from video_renderer.video_validator import FrameSequenceInfo


class ThumbnailGenerator(ABC):
    """Generate a thumbnail image from a frame sequence."""

    @abstractmethod
    def generate(
        self,
        sequence: FrameSequenceInfo,
        output_path: str | Path,
    ) -> str:
        ...


class MiddleFrameThumbnailGenerator(ThumbnailGenerator):
    """Copy the middle frame as thumbnail.png."""

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("video_renderer")

    def generate(
        self,
        sequence: FrameSequenceInfo,
        output_path: str | Path,
    ) -> str:
        if not sequence.frame_files:
            raise ValueError("No frames available for thumbnail")
        middle_idx = len(sequence.frame_files) // 2
        source = Path(sequence.frame_files[middle_idx])
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(source) as img:
            thumb = img.convert("RGBA")
            thumb.save(dest, format="PNG")

        self._log.info("THUMBNAIL_CREATED path=%s source=%s", dest, source)
        return str(dest)
