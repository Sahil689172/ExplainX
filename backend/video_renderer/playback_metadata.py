"""Playback metadata for Phase 6.1 timeline playback."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class PlaybackMetadata:
    """Summary of a completed playback / frame sequence render."""

    session_id: str
    scene_id: str
    scene_name: str
    fps: int
    duration: float
    frame_count: int
    exported_count: int
    output_directory: str
    start_time: str
    end_time: str
    render_time_seconds: float
    preview_mode: float = 1.0
    frame_range: tuple[int, int] | None = None
    time_range: tuple[float, float] | None = None
    timestamps: list[float] = field(default_factory=list)
    frame_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.frame_range:
            d["frame_range"] = list(self.frame_range)
        if self.time_range:
            d["time_range"] = list(self.time_range)
        return d

    @staticmethod
    def create(
        *,
        scene_id: str,
        scene_name: str,
        fps: int,
        duration: float,
        frame_count: int,
        exported_count: int,
        output_directory: str,
        render_time_seconds: float,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        preview_mode: float = 1.0,
        frame_range: tuple[int, int] | None = None,
        time_range: tuple[float, float] | None = None,
        timestamps: list[float] | None = None,
        frame_files: list[str] | None = None,
        session_id: str | None = None,
    ) -> PlaybackMetadata:
        now = datetime.now(timezone.utc)
        return PlaybackMetadata(
            session_id=session_id or str(uuid4()),
            scene_id=scene_id,
            scene_name=scene_name,
            fps=fps,
            duration=duration,
            frame_count=frame_count,
            exported_count=exported_count,
            output_directory=output_directory,
            start_time=(start_time or now).isoformat(),
            end_time=(end_time or now).isoformat(),
            render_time_seconds=round(render_time_seconds, 3),
            preview_mode=preview_mode,
            frame_range=frame_range,
            time_range=time_range,
            timestamps=list(timestamps or []),
            frame_files=list(frame_files or []),
        )
