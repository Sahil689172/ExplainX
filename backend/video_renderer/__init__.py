"""Phase 6.0 — Frame Rendering. Phase 6.1 — Timeline Playback. Phase 6.2 — Video Encoding."""

from video_renderer.camera_renderer import CameraRenderer
from video_renderer.compositor import Compositor
from video_renderer.encoder_config import CODEC_SETTINGS, CodecSettings, EncoderConfig, OutputFormat
from video_renderer.encoder_metadata import VideoMetadata
from video_renderer.encoding_profiles import EncodingProfile, PROFILES, get_profile
from video_renderer.ffmpeg_encoder import FFmpegCommand, FFmpegCommandBuilder, FFmpegExecutor, SubprocessFFmpegExecutor
from video_renderer.frame_engine import FrameEngine
from video_renderer.frame_exporter import FrameExporter
from video_renderer.frame_renderer import FrameRenderer
from video_renderer.frame_scheduler import FrameScheduler, ScheduledFrame
from video_renderer.fps_manager import FpsManager, SUPPORTED_FPS
from video_renderer.layer_manager import LayerManager
from video_renderer.playback_controller import PlaybackController, PlaybackMode, PlaybackRequest
from video_renderer.playback_metadata import PlaybackMetadata
from video_renderer.render_session import RenderSession
from video_renderer.scene_collection import (
    MergedTimeline,
    SceneClip,
    SceneCollection,
    SceneFrameStats,
)
from video_renderer.renderer_config import RendererConfig
from video_renderer.renderer_metadata import FrameRenderMetadata
from video_renderer.renderer_types import CameraState, LayerType, RenderLayer, TransformState
from video_renderer.thumbnail_generator import MiddleFrameThumbnailGenerator, ThumbnailGenerator
from video_renderer.timeline_player import TimelinePlayer
from video_renderer.transform_engine import TransformEngine
from video_renderer.video_encoder import FFmpegVideoEncoder, VideoEncoder, encode_collection, encode_video
from video_renderer.video_exporter import VideoExporter
from video_renderer.video_validator import (
    CorruptedFrameError,
    DefaultFrameValidator,
    EncodingPermissionError,
    FrameSequenceInfo,
    FrameValidator,
    MissingFFmpegError,
    MissingFramesError,
    VideoEncodingError,
)

__all__ = [
    "CameraRenderer",
    "CameraState",
    "CODEC_SETTINGS",
    "CodecSettings",
    "Compositor",
    "CorruptedFrameError",
    "DefaultFrameValidator",
    "EncoderConfig",
    "EncodingPermissionError",
    "EncodingProfile",
    "FFmpegCommand",
    "FFmpegCommandBuilder",
    "FFmpegExecutor",
    "FFmpegVideoEncoder",
    "FrameEngine",
    "FrameExporter",
    "FrameRenderMetadata",
    "FrameRenderer",
    "FrameScheduler",
    "FrameSequenceInfo",
    "FrameValidator",
    "FpsManager",
    "LayerManager",
    "LayerType",
    "MergedTimeline",
    "MiddleFrameThumbnailGenerator",
    "MissingFFmpegError",
    "MissingFramesError",
    "OutputFormat",
    "PlaybackController",
    "PlaybackMetadata",
    "PlaybackMode",
    "PlaybackRequest",
    "PROFILES",
    "RenderLayer",
    "RenderSession",
    "RendererConfig",
    "SceneClip",
    "SceneCollection",
    "SceneFrameStats",
    "ScheduledFrame",
    "SubprocessFFmpegExecutor",
    "SUPPORTED_FPS",
    "ThumbnailGenerator",
    "TimelinePlayer",
    "TransformEngine",
    "TransformState",
    "VideoEncoder",
    "VideoEncodingError",
    "VideoExporter",
    "VideoMetadata",
    "encode_collection",
    "encode_video",
    "get_profile",
]
