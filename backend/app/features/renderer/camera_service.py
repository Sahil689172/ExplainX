"""CameraService — smooth viewport motion over a static image."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.features.renderer.camera import lerp, viewport_for_scale
from app.features.renderer.camera_schemas import (
    CameraConfig,
    CameraMetadata,
    CameraType,
    Viewport,
)
from app.features.renderer.easing import apply_easing

_CAMERA_CONFIG_NAME = "camera.json"
_TYPE_LABELS = {
    CameraType.CENTER: "Center",
    CameraType.ZOOM_IN: "Zoom In",
    CameraType.ZOOM_OUT: "Zoom Out",
    CameraType.PAN_LEFT: "Pan Left",
    CameraType.PAN_RIGHT: "Pan Right",
    CameraType.PAN_UP: "Pan Up",
    CameraType.PAN_DOWN: "Pan Down",
}


class CameraService:
    """Compute viewports over time from a camera configuration."""

    def __init__(
        self,
        *,
        config: CameraConfig,
        image_width: int,
        image_height: int,
    ) -> None:
        self._config = config
        self._image_width = image_width
        self._image_height = image_height

    @property
    def config(self) -> CameraConfig:
        return self._config

    @classmethod
    def from_config(
        cls,
        *,
        config: CameraConfig,
        image_width: int,
        image_height: int,
    ) -> CameraService:
        return cls(config=config, image_width=image_width, image_height=image_height)

    @classmethod
    def from_project(
        cls,
        project_root: Path,
        settings: Settings,
        *,
        duration_sec: int,
        image_width: int,
        image_height: int,
    ) -> CameraService:
        config = load_camera_config(project_root, settings, duration_sec=duration_sec)
        return cls(config=config, image_width=image_width, image_height=image_height)

    def viewport_at_time(self, time_seconds: float) -> Viewport:
        """Return the viewport for ``time_seconds`` into the motion."""
        return self.get_viewport(time_seconds)

    def get_viewport(self, time_seconds: float) -> Viewport:
        """Alias for ``viewport_at_time`` (integration contract)."""
        duration = float(self._config.duration)
        raw_t = 0.0 if duration <= 0 else max(0.0, min(time_seconds / duration, 1.0))
        eased = apply_easing(self._config.easing, raw_t)
        return self._viewport_for_progress(eased)

    def scale_at_time(self, time_seconds: float) -> float:
        """Return the interpolated scale at ``time_seconds`` (for debug / metadata)."""
        duration = float(self._config.duration)
        raw_t = 0.0 if duration <= 0 else max(0.0, min(time_seconds / duration, 1.0))
        eased = apply_easing(self._config.easing, raw_t)
        cfg = self._config
        if cfg.type == CameraType.CENTER:
            return 1.0
        if cfg.type in {CameraType.ZOOM_IN, CameraType.ZOOM_OUT}:
            return lerp(cfg.start_scale, cfg.end_scale, eased)
        return cfg.start_scale

    def metadata(self) -> CameraMetadata:
        return CameraMetadata(
            camera_type=self._config.type.value,
            start_scale=self._config.start_scale,
            end_scale=self._config.end_scale,
            zoom=max(self._config.start_scale, self._config.end_scale),
            duration=self._config.duration,
            easing=self._config.easing,
        )

    def log_camera(self) -> None:
        label = _TYPE_LABELS.get(self._config.type, self._config.type.value)
        print("[Camera]", flush=True)
        print(f"Type : {label}", flush=True)
        if self._config.type in {
            CameraType.ZOOM_IN,
            CameraType.ZOOM_OUT,
            CameraType.CENTER,
        }:
            print(
                f"Scale : {self._config.start_scale} -> {self._config.end_scale}",
                flush=True,
            )
        else:
            print(f"Scale : {self._config.start_scale}", flush=True)
        print(f"Duration : {self._config.duration} sec", flush=True)

    def _viewport_for_progress(self, eased: float) -> Viewport:
        cfg = self._config
        iw, ih = self._image_width, self._image_height

        if cfg.type == CameraType.CENTER:
            scale = 1.0
            return viewport_for_scale(image_width=iw, image_height=ih, scale=scale)

        if cfg.type == CameraType.ZOOM_IN:
            scale = lerp(cfg.start_scale, cfg.end_scale, eased)
            return viewport_for_scale(image_width=iw, image_height=ih, scale=scale)

        if cfg.type == CameraType.ZOOM_OUT:
            scale = lerp(cfg.start_scale, cfg.end_scale, eased)
            return viewport_for_scale(image_width=iw, image_height=ih, scale=scale)

        scale = cfg.start_scale
        pan_x = 0.5
        pan_y = 0.5

        if cfg.type == CameraType.PAN_LEFT:
            pan_x = lerp(1.0, 0.0, eased)
        elif cfg.type == CameraType.PAN_RIGHT:
            pan_x = lerp(0.0, 1.0, eased)
        elif cfg.type == CameraType.PAN_UP:
            pan_y = lerp(1.0, 0.0, eased)
        elif cfg.type == CameraType.PAN_DOWN:
            pan_y = lerp(0.0, 1.0, eased)

        return viewport_for_scale(
            image_width=iw,
            image_height=ih,
            scale=scale,
            pan_x=pan_x,
            pan_y=pan_y,
        )


def load_camera_config(
    project_root: Path,
    settings: Settings,
    *,
    duration_sec: int,
) -> CameraConfig:
    """Load ``artifacts/camera.json`` or build defaults from Settings."""
    path = project_root / "artifacts" / _CAMERA_CONFIG_NAME
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            config = CameraConfig.model_validate(data)
        except (OSError, ValueError) as exc:
            raise ValidationAppError(
                "Invalid camera.json configuration.",
                code="CAMERA_CONFIG_INVALID",
                details={"path": str(path), "error": str(exc)},
            ) from exc
        return config.model_copy(update={"duration": duration_sec})
    return default_camera_config(settings, duration_sec=duration_sec)


def default_camera_config(settings: Settings, *, duration_sec: int) -> CameraConfig:
    """Build camera config from Settings when ``camera.json`` is absent."""
    raw_type = (settings.default_camera or "center").strip().lower()
    try:
        camera_type = CameraType(raw_type)
    except ValueError as exc:
        raise ValidationAppError(
            f"Unsupported DEFAULT_CAMERA: {raw_type!r}.",
            code="CAMERA_CONFIG_INVALID",
            details={
                "default_camera": raw_type,
                "supported": [t.value for t in CameraType],
            },
        ) from exc

    easing = (settings.default_easing or "ease_in_out").strip().lower()
    zoom = float(settings.default_zoom)
    if zoom < 1.0:
        raise ValidationAppError(
            "DEFAULT_ZOOM must be at least 1.0.",
            code="CAMERA_INVALID_ZOOM",
            details={"default_zoom": zoom},
        )

    start_scale = 1.0
    end_scale = 1.0
    if camera_type == CameraType.ZOOM_IN:
        start_scale = 1.0
        end_scale = zoom
    elif camera_type == CameraType.ZOOM_OUT:
        start_scale = zoom
        end_scale = 1.0
    elif camera_type in {
        CameraType.PAN_LEFT,
        CameraType.PAN_RIGHT,
        CameraType.PAN_UP,
        CameraType.PAN_DOWN,
    }:
        # Pan at a fixed zoom so the viewport has room to move.
        start_scale = zoom
        end_scale = zoom
    # CENTER keeps 1.0 → 1.0

    return CameraConfig(
        type=camera_type,
        start_scale=start_scale,
        end_scale=end_scale,
        duration=duration_sec,
        easing=easing,
    )
