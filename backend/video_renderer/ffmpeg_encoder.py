"""FFmpeg command builder and executor."""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from image_generation.logger import get_engine_logger
from video_renderer.encoder_config import CODEC_SETTINGS, EncoderConfig, OutputFormat
from video_renderer.encoding_profiles import EncodingProfile
from video_renderer.video_validator import FrameSequenceInfo, MissingFFmpegError, VideoEncodingError


@dataclass(slots=True)
class FFmpegCommand:
    """Built FFmpeg invocation."""

    command: list[str]
    output_path: str
    format: OutputFormat


class FFmpegExecutor(ABC):
    """Execute FFmpeg commands."""

    @abstractmethod
    def run(self, command: FFmpegCommand, *, timeout: int = 600) -> None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class SubprocessFFmpegExecutor(FFmpegExecutor):
    """Run FFmpeg via subprocess."""

    def __init__(self, *, config: EncoderConfig | None = None, logger=None) -> None:
        self._config = config or EncoderConfig()
        self._log = logger or get_engine_logger("video_renderer")

    def is_available(self) -> bool:
        return shutil.which(self._config.ffmpeg_path) is not None

    def run(self, command: FFmpegCommand, *, timeout: int | None = None) -> None:
        if not self.is_available():
            raise MissingFFmpegError(
                f"FFmpeg not found on PATH ('{self._config.ffmpeg_path}'). Install FFmpeg to encode video."
            )
        timeout = timeout or self._config.timeout_seconds
        self._log.info("ENCODING_PROGRESS command=%s", " ".join(command.command))
        try:
            result = subprocess.run(
                command.command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VideoEncodingError(f"FFmpeg encoding timed out after {timeout}s") from exc
        except OSError as exc:
            raise VideoEncodingError(f"Failed to execute FFmpeg: {exc}") from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise VideoEncodingError(
                f"FFmpeg encoding failed (exit {result.returncode}): {stderr[-500:]}"
            )
        self._log.info("ENCODING_COMPLETED path=%s", command.output_path)


class FFmpegCommandBuilder:
    """Build FFmpeg commands for frame sequences."""

    def __init__(self, *, config: EncoderConfig | None = None, logger=None) -> None:
        self._config = config or EncoderConfig()
        self._log = logger or get_engine_logger("video_renderer")

    def build(
        self,
        sequence: FrameSequenceInfo,
        output_path: str | Path,
        *,
        output_format: OutputFormat,
        profile: EncodingProfile,
    ) -> FFmpegCommand:
        fmt = output_format
        if fmt not in CODEC_SETTINGS:
            raise VideoEncodingError(f"Unsupported output format: {fmt.value}")

        settings = CODEC_SETTINGS[fmt]
        crf = profile.mp4_crf if fmt == OutputFormat.MP4 else profile.webm_crf
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        input_pattern = str(Path(sequence.frame_directory) / self._config.frame_pattern)
        scale = self._scale_filter(sequence.width, sequence.height, profile)

        cmd: list[str] = [self._config.ffmpeg_path]
        if self._config.overwrite:
            cmd.append("-y")
        cmd.extend(
            [
                "-r",
                str(sequence.fps),
                "-i",
                input_pattern,
                "-vf",
                scale,
                "-c:v",
                settings.codec,
                "-pix_fmt",
                settings.pixel_format,
                "-crf",
                str(crf),
            ]
        )
        if settings.preset:
            cmd.extend(["-preset", settings.preset])
        if self._config.threads > 0:
            cmd.extend(["-threads", str(self._config.threads)])

        # Bitrate cap from profile (x264; VP9 uses CRF + -b:v 0)
        if fmt == OutputFormat.MP4:
            maxrate_k = int(profile.bitrate_mbps * 1000)
            cmd.extend(["-maxrate", f"{maxrate_k}k", "-bufsize", f"{maxrate_k * 2}k"])
        cmd.extend(settings.extra_args)
        cmd.append(str(out))

        command = FFmpegCommand(command=cmd, output_path=str(out), format=fmt)
        self._log.info("FFMPEG_COMMAND_BUILT format=%s output=%s", fmt.value, out)
        return command

    @staticmethod
    def _scale_filter(src_w: int, src_h: int, profile: EncodingProfile) -> str:
        if src_w == profile.width and src_h == profile.height:
            return f"scale={profile.width}:{profile.height}"
        return (
            f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,"
            f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2"
        )
