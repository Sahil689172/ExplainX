"""Camera motion schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.features.renderer.easing import EASING_NAMES


class CameraType(str, Enum):
    CENTER = "center"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"


class CameraConfig(BaseModel):
    """Parameter-driven camera motion definition."""

    type: CameraType
    start_scale: float = Field(default=1.0, ge=1.0)
    end_scale: float = Field(default=1.0, ge=1.0)
    duration: int = Field(default=60, ge=1, le=3600)
    easing: str = Field(default="ease_in_out")

    @field_validator("easing")
    @classmethod
    def validate_easing(cls, value: str) -> str:
        key = (value or "").strip().lower()
        if key not in EASING_NAMES:
            raise ValueError(f"easing must be one of {sorted(EASING_NAMES)}")
        return key

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class Viewport(BaseModel):
    """Crop rectangle in source-image pixel coordinates."""

    x: float = Field(ge=0.0)
    y: float = Field(ge=0.0)
    width: float = Field(gt=0.0)
    height: float = Field(gt=0.0)


class CameraMetadata(BaseModel):
    """Persisted camera summary (artifacts/camera_metadata.json)."""

    camera_type: str
    start_scale: float
    end_scale: float
    duration: int
    easing: str
