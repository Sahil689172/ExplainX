"""Video encoder — convert PNG frame sequences to MP4 / WebM."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence, TYPE_CHECKING

from image_generation.logger import get_engine_logger
from video_renderer.encoder_config import EncoderConfig, OutputFormat
from video_renderer.encoder_metadata import VideoMetadata
from video_renderer.encoding_profiles import EncodingProfile, get_profile
from video_renderer.ffmpeg_encoder import FFmpegCommandBuilder, FFmpegExecutor, SubprocessFFmpegExecutor
from video_renderer.playback_metadata import PlaybackMetadata
from video_renderer.thumbnail_generator import MiddleFrameThumbnailGenerator, ThumbnailGenerator
from video_renderer.video_exporter import VideoExporter
from video_renderer.video_validator import DefaultFrameValidator, EncodingPermissionError, FrameValidator, VideoEncodingError

if TYPE_CHECKING:
    from video_renderer.scene_collection import MergedTimeline


class VideoEncoder(ABC):
    """Encode a frame sequence into video files."""

    @abstractmethod
    def encode_video(
        self,
        frame_directory: str | Path,
        fps: int,
        output_format: str | OutputFormat,
        profile: str | EncodingProfile,
        *,
        scene_metadata: dict[str, Any] | None = None,
        playback_metadata: PlaybackMetadata | dict[str, Any] | None = None,
        output_dir: str | Path = "output",
        formats: Sequence[str | OutputFormat] | None = None,
    ) -> VideoMetadata:
        ...


class FFmpegVideoEncoder(VideoEncoder):
    """FFmpeg-backed video encoder — independent of rendering."""

    def __init__(
        self,
        *,
        validator: FrameValidator | None = None,
        command_builder: FFmpegCommandBuilder | None = None,
        executor: FFmpegExecutor | None = None,
        thumbnail_generator: ThumbnailGenerator | None = None,
        exporter: VideoExporter | None = None,
        config: EncoderConfig | None = None,
        logger=None,
    ) -> None:
        self._config = config or EncoderConfig()
        self._validator = validator or DefaultFrameValidator()
        self._builder = command_builder or FFmpegCommandBuilder(config=self._config)
        self._executor = executor or SubprocessFFmpegExecutor(config=self._config)
        self._thumbnails = thumbnail_generator or MiddleFrameThumbnailGenerator()
        self._exporter = exporter or VideoExporter()
        self._log = logger or get_engine_logger("video_renderer")

    def encode_video(
        self,
        frame_directory: str | Path,
        fps: int,
        output_format: str | OutputFormat,
        profile: str | EncodingProfile,
        *,
        scene_metadata: dict[str, Any] | None = None,
        playback_metadata: PlaybackMetadata | dict[str, Any] | None = None,
        output_dir: str | Path = "output",
        formats: Sequence[str | OutputFormat] | None = None,
    ) -> VideoMetadata:
        enc_profile = profile if isinstance(profile, EncodingProfile) else get_profile(str(profile))
        scene = scene_metadata or {}
        playback = self._normalize_playback(playback_metadata)

        scene_id = str(scene.get("scene_id") or playback.get("scene_id") or "unknown")
        scene_name = str(
            scene.get("title")
            or playback.get("scene_name")
            or scene.get("topic")
            or "scene"
        )
        expected_count = playback.get("exported_count")

        self._log.info(
            "ENCODING_STARTED scene_id=%s fps=%s profile=%s dir=%s",
            scene_id,
            fps,
            enc_profile.profile_id,
            frame_directory,
        )

        sequence = self._validator.validate(
            frame_directory,
            fps=fps,
            expected_count=expected_count,
        )

        video_dir = self._exporter.scene_video_dir(output_dir, scene_name)
        self._ensure_writable(video_dir)

        target_formats = self._resolve_formats(output_format, formats)
        mp4_path = webm_path = None
        primary_codec = ""
        total_size = 0
        t0 = time.perf_counter()

        for fmt in target_formats:
            out_name = "video.mp4" if fmt == OutputFormat.MP4 else "video.webm"
            out_path = video_dir / out_name
            command = self._builder.build(
                sequence, out_path, output_format=fmt, profile=enc_profile
            )
            self._executor.run(command)
            primary_codec = command.command[command.command.index("-c:v") + 1]
            size = out_path.stat().st_size
            total_size += size
            if fmt == OutputFormat.MP4:
                mp4_path = str(out_path)
            elif fmt == OutputFormat.WEBM:
                webm_path = str(out_path)
            self._log.info("VIDEO_EXPORTED format=%s path=%s size=%s", fmt.value, out_path, size)

        thumb_path = self._thumbnails.generate(
            sequence, video_dir / "thumbnail.png"
        )

        encoding_time = time.perf_counter() - t0
        metadata = VideoMetadata.create(
            scene_id=scene_id,
            scene_name=scene_name,
            fps=sequence.fps,
            duration=sequence.duration,
            resolution=(enc_profile.width, enc_profile.height),
            codec=primary_codec,
            bitrate_mbps=enc_profile.bitrate_mbps,
            frame_count=sequence.frame_count,
            render_profile=enc_profile.profile_id,
            encoding_time_seconds=encoding_time,
            video_size_bytes=total_size,
            thumbnail_path=thumb_path,
            mp4_path=mp4_path,
            webm_path=webm_path,
            output_directory=str(video_dir),
            formats=[f.value for f in target_formats],
        )
        meta_path = self._exporter.export_metadata(metadata, video_dir)
        metadata.metadata_path = meta_path
        return metadata

    @staticmethod
    def _ensure_writable(directory: Path) -> None:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            raise EncodingPermissionError(
                f"Output directory not writable: {directory}"
            ) from exc

    @staticmethod
    def _normalize_playback(
        playback: PlaybackMetadata | dict[str, Any] | None,
    ) -> dict[str, Any]:
        if playback is None:
            return {}
        if isinstance(playback, PlaybackMetadata):
            return playback.to_dict()
        return dict(playback)

    @staticmethod
    def _resolve_formats(
        primary: str | OutputFormat,
        formats: Sequence[str | OutputFormat] | None,
    ) -> list[OutputFormat]:
        if formats:
            out: list[OutputFormat] = []
            for f in formats:
                key = f.value if isinstance(f, OutputFormat) else str(f).lower().lstrip(".")
                if key in ("mp4", "webm"):
                    out.append(OutputFormat(key))
            if out:
                return out
        if isinstance(primary, OutputFormat):
            return [primary]
        key = str(primary).lower().lstrip(".")
        if key in ("both", "all", ""):
            return [OutputFormat.MP4, OutputFormat.WEBM]
        return [OutputFormat(key)]


def encode_collection(
    merged: "MergedTimeline",
    *,
    output_format: str | OutputFormat = "mp4",
    profile: str | EncodingProfile = "standard",
    scene_metadata: dict[str, Any] | None = None,
    output_dir: str | Path = "output",
    encoder: VideoEncoder | None = None,
) -> VideoMetadata:
    """Encode a :class:`~video_renderer.scene_collection.MergedTimeline` once.

    This is the stabilized entry point: the encoder receives the merged output
    of :class:`~video_renderer.scene_collection.SceneCollection`, not individual
    scene frame directories.
    """
    from video_renderer.scene_collection import MergedTimeline as _MergedTimeline

    if not isinstance(merged, _MergedTimeline):
        raise TypeError(f"Expected MergedTimeline, got {type(merged).__name__}")

    playback = PlaybackMetadata.create(
        scene_id=str((scene_metadata or {}).get("scene_id", "collection")),
        scene_name=str((scene_metadata or {}).get("title", "collection")),
        fps=merged.fps,
        duration=merged.duration,
        frame_count=merged.frame_count,
        exported_count=merged.frame_count,
        output_directory=str(merged.frame_directory),
        render_time_seconds=0.0,
    )
    return encode_video(
        merged.frame_directory,
        fps=merged.fps,
        output_format=output_format,
        profile=profile,
        scene_metadata=scene_metadata,
        playback_metadata=playback,
        output_dir=output_dir,
        encoder=encoder,
    )


def encode_video(
    frame_directory: str | Path,
    fps: int,
    output_format: str | OutputFormat = "both",
    profile: str | EncodingProfile = "preview",
    *,
    scene_metadata: dict[str, Any] | None = None,
    playback_metadata: PlaybackMetadata | dict[str, Any] | None = None,
    output_dir: str | Path = "output",
    formats: Sequence[str | OutputFormat] | None = None,
    encoder: VideoEncoder | None = None,
) -> VideoMetadata:
    """Encode a rendered PNG frame sequence into video files.

    Returns :class:`VideoMetadata` with paths to MP4/WebM, thumbnail, and metadata JSON.
    """
    impl = encoder or FFmpegVideoEncoder()
    return impl.encode_video(
        frame_directory,
        fps,
        output_format,
        profile,
        scene_metadata=scene_metadata,
        playback_metadata=playback_metadata,
        output_dir=output_dir,
        formats=formats,
    )
