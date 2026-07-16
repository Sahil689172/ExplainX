"""Scene composition schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.features.renderer.camera_schemas import CameraConfig, CameraType
from app.features.renderer.easing import EASING_NAMES


class SceneCameraSettings(BaseModel):
    """Per-scene camera parameters (Phase 2 engine)."""

    start_scale: float = Field(default=1.0, ge=1.0)
    end_scale: float = Field(default=1.0, ge=1.0)
    easing: str = Field(default="ease_in_out")

    @field_validator("easing")
    @classmethod
    def validate_easing(cls, value: str) -> str:
        key = (value or "").strip().lower()
        if key not in EASING_NAMES:
            raise ValueError(f"easing must be one of {sorted(EASING_NAMES)}")
        return key


class SceneDefinition(BaseModel):
    """One scene in a multi-scene render."""

    scene_id: str = Field(min_length=1, max_length=64)
    image: str = Field(min_length=1, description="Image path relative to project root")
    duration: int = Field(ge=1, le=3600, description="Scene duration in seconds")
    camera: CameraType = Field(default=CameraType.CENTER)
    camera_settings: SceneCameraSettings = Field(default_factory=SceneCameraSettings)

    @field_validator("camera", mode="before")
    @classmethod
    def normalize_camera(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    def to_camera_config(self) -> CameraConfig:
        """Build a Phase 2 ``CameraConfig`` for this scene."""
        settings = self.camera_settings
        return CameraConfig(
            type=self.camera,
            start_scale=settings.start_scale,
            end_scale=settings.end_scale,
            duration=self.duration,
            easing=settings.easing,
        )


class SceneManifest(BaseModel):
    """``artifacts/scene_manifest.json`` — ordered list of scenes."""

    video_duration: int | None = Field(default=None, ge=1, le=7200)
    fps: int | None = Field(default=None, ge=1, le=120)
    scenes: list[SceneDefinition] = Field(min_length=1)


class SceneRenderRecord(BaseModel):
    """Per-scene summary written to ``scene_metadata.json``."""

    scene_id: str
    image: str
    duration_seconds: int
    frames: int
    camera: str


class SceneMetadata(BaseModel):
    """Persisted multi-scene render summary."""

    scene_count: int
    scene_duration: list[int]
    frames_per_scene: list[int]
    camera_used: list[str]
    total_frames: int
    fps: int
    video_duration: int
    scenes: list[SceneRenderRecord]
