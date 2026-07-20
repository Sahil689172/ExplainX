"""Video encoding metadata for Phase 6.2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class VideoMetadata:
    """Result of encoding a frame sequence into video."""

    video_id: str
    scene_id: str
    scene_name: str
    fps: int
    duration: float
    resolution: tuple[int, int]
    codec: str
    bitrate_mbps: float
    frame_count: int
    render_profile: str
    encoding_time_seconds: float
    video_size_bytes: int
    thumbnail_path: str | None
    mp4_path: str | None = None
    webm_path: str | None = None
    output_directory: str = ""
    metadata_path: str | None = None
    created_at: str = ""
    formats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["resolution"] = list(self.resolution)
        return d

    @staticmethod
    def create(
        *,
        scene_id: str,
        scene_name: str,
        fps: int,
        duration: float,
        resolution: tuple[int, int],
        codec: str,
        bitrate_mbps: float,
        frame_count: int,
        render_profile: str,
        encoding_time_seconds: float,
        video_size_bytes: int,
        thumbnail_path: str | None,
        mp4_path: str | None = None,
        webm_path: str | None = None,
        output_directory: str = "",
        metadata_path: str | None = None,
        formats: list[str] | None = None,
        video_id: str | None = None,
    ) -> VideoMetadata:
        return VideoMetadata(
            video_id=video_id or str(uuid4()),
            scene_id=scene_id,
            scene_name=scene_name,
            fps=fps,
            duration=duration,
            resolution=resolution,
            codec=codec,
            bitrate_mbps=bitrate_mbps,
            frame_count=frame_count,
            render_profile=render_profile,
            encoding_time_seconds=round(encoding_time_seconds, 3),
            video_size_bytes=video_size_bytes,
            thumbnail_path=thumbnail_path,
            mp4_path=mp4_path,
            webm_path=webm_path,
            output_directory=output_directory,
            metadata_path=metadata_path,
            created_at=datetime.now(timezone.utc).isoformat(),
            formats=list(formats or []),
        )
