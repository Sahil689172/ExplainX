"""Scene composition schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

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


class SceneObjectDefinition(BaseModel):
    """One object placed on a scene background (Phase 4 / 4.5)."""

    id: str = Field(min_length=1, max_length=64)
    image: str = Field(min_length=1, description="Image path relative to project root")
    x: float = 0.0
    y: float = 0.0
    scale: float = Field(default=1.0, gt=0.0)
    display_width: int | None = Field(
        default=None,
        gt=0,
        description="Logical on-screen width in pixels; overrides scale when set",
    )
    rotation: float = 0.0
    z_index: int = 0
    visible: bool = True
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)


class SceneDefinition(BaseModel):
    """One scene in a multi-scene render.

    Legacy (Phase 3): ``image`` only.
    Phase 4: ``background`` + optional ``objects`` (``image`` still accepted as background).
    """

    scene_id: str = Field(min_length=1, max_length=64)
    image: str | None = Field(
        default=None,
        description="Legacy single-image scene (treated as background when alone)",
    )
    background: str | None = Field(
        default=None,
        description="Background image for layered scenes",
    )
    objects: list[SceneObjectDefinition] = Field(default_factory=list)
    duration: int = Field(ge=1, le=3600, description="Scene duration in seconds")
    camera: CameraType = Field(default=CameraType.CENTER)
    camera_settings: SceneCameraSettings = Field(default_factory=SceneCameraSettings)

    @field_validator("camera", mode="before")
    @classmethod
    def normalize_camera(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("image", "background", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def require_visual_source(self) -> SceneDefinition:
        if not self.image and not self.background:
            raise ValueError("Scene must define 'image' (legacy) or 'background'.")
        return self

    def is_layered(self) -> bool:
        """True when Phase 4 background/objects path should run."""
        return self.background is not None or bool(self.objects)

    def background_ref(self) -> str:
        """Resolved background path string (background preferred, else legacy image)."""
        if self.background:
            return self.background
        if self.image:
            return self.image
        raise ValueError("Scene has no background or image.")

    def primary_image_ref(self) -> str:
        """Image label used in logs / metadata."""
        return self.background_ref()

    def to_camera_config(self, *, default_zoom: float = 1.15) -> CameraConfig:
        """Build a Phase 2 ``CameraConfig`` for this scene.

        Manifests often set only ``camera`` (e.g. ``zoom_in``) without
        ``camera_settings``.  Default scales are 1.0→1.0, which is a no-op for
        zoom/pan.  When both scales are still 1.0, apply the same type-aware
        defaults as Phase 2 ``default_camera_config``.
        """
        settings = self.camera_settings
        start_scale = settings.start_scale
        end_scale = settings.end_scale
        zoom = max(1.0, float(default_zoom))

        if start_scale == 1.0 and end_scale == 1.0:
            if self.camera == CameraType.ZOOM_IN:
                start_scale, end_scale = 1.0, zoom
            elif self.camera == CameraType.ZOOM_OUT:
                start_scale, end_scale = zoom, 1.0
            elif self.camera in {
                CameraType.PAN_LEFT,
                CameraType.PAN_RIGHT,
                CameraType.PAN_UP,
                CameraType.PAN_DOWN,
            }:
                # Fixed zoom so the viewport has room to pan.
                start_scale, end_scale = zoom, zoom

        return CameraConfig(
            type=self.camera,
            start_scale=start_scale,
            end_scale=end_scale,
            duration=self.duration,
            easing=settings.easing,
        )


class SceneManifest(BaseModel):
    """``scene_manifest.json`` (artifacts/ or project root) — ordered scenes."""

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
    object_count: int = 0
    layered: bool = False


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
