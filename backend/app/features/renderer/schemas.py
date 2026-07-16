"""Renderer MVP schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RenderConfig(BaseModel):
    """Static-image render parameters."""

    fps: int = Field(ge=1, le=120)
    duration_sec: int = Field(ge=1, le=3600)
    frame_format: str = Field(default="png", min_length=2, max_length=8)

    @property
    def frame_count(self) -> int:
        return self.fps * self.duration_sec


class RenderMetadata(BaseModel):
    """Persisted render summary (artifacts/render_metadata.json)."""

    fps: int
    duration: int
    frame_count: int
    resolution: str
    render_time: float
    input_image: str
    output_video: str = "video.mp4"
