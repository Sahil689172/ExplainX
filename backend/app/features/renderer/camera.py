"""Viewport math for camera motion (pure functions, no I/O)."""

from __future__ import annotations

from app.core.errors import ValidationAppError
from app.features.renderer.camera_schemas import Viewport


def lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


def validate_viewport(
    viewport: Viewport,
    *,
    image_width: int,
    image_height: int,
    output_width: int,
    output_height: int,
    tolerance: float = 0.5,
) -> None:
    """Reject viewports outside the image or with distorted aspect ratio."""
    if viewport.width <= 0 or viewport.height <= 0:
        raise ValidationAppError(
            "Viewport dimensions must be positive.",
            code="CAMERA_INVALID_VIEWPORT",
            details={"width": viewport.width, "height": viewport.height},
        )

    if viewport.x < -tolerance or viewport.y < -tolerance:
        raise ValidationAppError(
            "Viewport origin must be non-negative.",
            code="CAMERA_INVALID_VIEWPORT",
            details={"x": viewport.x, "y": viewport.y},
        )

    if viewport.x + viewport.width > image_width + tolerance:
        raise ValidationAppError(
            "Viewport extends beyond image width.",
            code="CAMERA_VIEWPORT_OUT_OF_BOUNDS",
            details={
                "x": viewport.x,
                "width": viewport.width,
                "image_width": image_width,
            },
        )

    if viewport.y + viewport.height > image_height + tolerance:
        raise ValidationAppError(
            "Viewport extends beyond image height.",
            code="CAMERA_VIEWPORT_OUT_OF_BOUNDS",
            details={
                "y": viewport.y,
                "height": viewport.height,
                "image_height": image_height,
            },
        )

    image_aspect = image_width / image_height
    viewport_aspect = viewport.width / viewport.height
    output_aspect = output_width / output_height
    if abs(viewport_aspect - image_aspect) > 0.02:
        raise ValidationAppError(
            "Viewport aspect ratio must match the source image.",
            code="CAMERA_ASPECT_RATIO_MISMATCH",
            details={
                "viewport_aspect": round(viewport_aspect, 4),
                "image_aspect": round(image_aspect, 4),
            },
        )
    if abs(output_aspect - image_aspect) > 0.02:
        raise ValidationAppError(
            "Output aspect ratio must match the source image.",
            code="CAMERA_ASPECT_RATIO_MISMATCH",
            details={
                "output_aspect": round(output_aspect, 4),
                "image_aspect": round(image_aspect, 4),
            },
        )


def viewport_for_scale(
    *,
    image_width: int,
    image_height: int,
    scale: float,
    pan_x: float = 0.5,
    pan_y: float = 0.5,
) -> Viewport:
    """Build a centered (or panned) viewport at ``scale`` (scale >= 1)."""
    if scale < 1.0:
        raise ValidationAppError(
            "Zoom scale must be at least 1.0.",
            code="CAMERA_INVALID_ZOOM",
            details={"scale": scale},
        )

    width = image_width / scale
    height = image_height / scale
    max_x = image_width - width
    max_y = image_height - height
    px = max(0.0, min(1.0, pan_x))
    py = max(0.0, min(1.0, pan_y))
    x = max_x * px
    y = max_y * py

    viewport = Viewport(x=x, y=y, width=width, height=height)
    validate_viewport(
        viewport,
        image_width=image_width,
        image_height=image_height,
        output_width=image_width,
        output_height=image_height,
    )
    return viewport
