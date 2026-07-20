"""Frame sequence validation before video encoding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from image_generation.logger import get_engine_logger
from video_renderer.fps_manager import FpsManager, SUPPORTED_FPS


class VideoEncodingError(Exception):
    """Base error for encoding failures."""


class MissingFFmpegError(VideoEncodingError):
    """FFmpeg binary not found."""


class MissingFramesError(VideoEncodingError):
    """Frame sequence incomplete or missing."""


class CorruptedFrameError(VideoEncodingError):
    """A frame file could not be read."""


class EncodingPermissionError(VideoEncodingError):
    """Output directory not writable."""


@dataclass(slots=True)
class FrameSequenceInfo:
    """Validated frame sequence metadata."""

    frame_directory: str
    frame_count: int
    fps: int
    width: int
    height: int
    frame_files: list[str]
    duration: float


class FrameValidator(ABC):
    """Validate a rendered PNG frame sequence."""

    @abstractmethod
    def validate(
        self,
        frame_directory: str | Path,
        *,
        fps: int,
        expected_count: int | None = None,
    ) -> FrameSequenceInfo:
        ...


class DefaultFrameValidator(FrameValidator):
    """Validate frames exist, are sequential, and share resolution."""

    def __init__(self, *, fps_manager: FpsManager | None = None, logger=None) -> None:
        self._fps = fps_manager or FpsManager()
        self._log = logger or get_engine_logger("video_renderer")

    def validate(
        self,
        frame_directory: str | Path,
        *,
        fps: int,
        expected_count: int | None = None,
    ) -> FrameSequenceInfo:
        directory = Path(frame_directory)
        if not directory.is_dir():
            raise MissingFramesError(f"Frame directory not found: {directory}")

        fps = self._fps.resolve(fps)
        if fps not in SUPPORTED_FPS and fps not in (120,):
            raise VideoEncodingError(f"Unsupported FPS: {fps}")

        frames = sorted(directory.glob("frame_*.png"))
        if not frames:
            raise MissingFramesError(f"No PNG frames found in {directory}")

        # Verify sequential numbering frame_000000 ... frame_N
        indices: list[int] = []
        for path in frames:
            stem = path.stem
            if not stem.startswith("frame_"):
                continue
            try:
                indices.append(int(stem.split("_", 1)[1]))
            except ValueError as exc:
                raise MissingFramesError(f"Invalid frame name: {path.name}") from exc

        indices.sort()
        if not indices:
            raise MissingFramesError(f"No PNG frames found in {directory}")

        expected_indices = list(range(indices[-1] + 1))
        if indices != expected_indices:
            missing = set(expected_indices) - set(indices)
            raise MissingFramesError(
                f"Missing frame numbers in sequence: {sorted(missing)[:5]}"
            )

        if expected_count is not None and len(indices) != expected_count:
            raise MissingFramesError(
                f"Expected {expected_count} frames, found {len(indices)}"
            )

        width = height = 0
        frame_files: list[str] = []
        for path in frames:
            try:
                with Image.open(path) as img:
                    if width == 0:
                        width, height = img.size
                    elif img.size != (width, height):
                        raise VideoEncodingError(
                            f"Inconsistent resolution: {path.name} is {img.size}, expected {(width, height)}"
                        )
            except OSError as exc:
                raise CorruptedFrameError(f"Corrupted frame: {path}") from exc
            frame_files.append(str(path))
            self._log.info("FRAME_VALIDATED path=%s", path)

        duration = len(indices) / fps
        return FrameSequenceInfo(
            frame_directory=str(directory),
            frame_count=len(indices),
            fps=fps,
            width=width,
            height=height,
            frame_files=frame_files,
            duration=duration,
        )
