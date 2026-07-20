"""Encoder configuration for Phase 6.2 Video Encoding Engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OutputFormat(str, Enum):
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"  # future
    AVI = "avi"  # future
    AV1 = "av1"  # future


@dataclass(slots=True)
class EncoderConfig:
    """Runtime encoder settings."""

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    frame_pattern: str = "frame_%06d.png"
    frame_pad_width: int = 6
    threads: int = 0
    overwrite: bool = True
    timeout_seconds: int = 600


@dataclass(slots=True)
class CodecSettings:
    """Per-format codec configuration."""

    format: OutputFormat
    codec: str
    crf: int
    pixel_format: str
    preset: str | None = None  # libx264 only
    extra_args: tuple[str, ...] = ()


CODEC_SETTINGS: dict[OutputFormat, CodecSettings] = {
    OutputFormat.MP4: CodecSettings(
        format=OutputFormat.MP4,
        codec="libx264",
        crf=18,
        preset="medium",
        pixel_format="yuv420p",
        extra_args=("-movflags", "+faststart"),
    ),
    OutputFormat.WEBM: CodecSettings(
        format=OutputFormat.WEBM,
        codec="libvpx-vp9",
        crf=30,
        pixel_format="yuv420p",
        extra_args=("-b:v", "0", "-deadline", "good", "-cpu-used", "2"),
    ),
}
