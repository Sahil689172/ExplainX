"""Generate frame files from a static image with optional camera motion."""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

from app.core.errors import ExplainXError, NotFoundError, ValidationAppError
from app.features.renderer.camera_schemas import Viewport
from app.features.renderer.camera_service import CameraService
from app.features.renderer.schemas import RenderConfig

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
_SEARCH_DIRS = ("assets", "source", "artifacts")


def even_dimensions(width: int, height: int) -> tuple[int, int]:
    """Snap to nearest even size that is ≤ the given size (libx264-safe)."""
    w = max(2, int(width) - (int(width) % 2))
    h = max(2, int(height) - (int(height) % 2))
    return w, h


def discover_input_image(project_root: Path) -> Path:
    """Locate the first PNG/JPG under assets, source, then artifacts."""
    candidates: list[Path] = []
    for subdir in _SEARCH_DIRS:
        base = project_root / subdir
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES:
                candidates.append(path)

    if not candidates:
        raise NotFoundError(
            "No input image (PNG/JPG) found for this project.",
            code="RENDER_INPUT_IMAGE_NOT_FOUND",
            details={
                "searched": [str(project_root / d) for d in _SEARCH_DIRS],
                "formats": sorted(_IMAGE_SUFFIXES),
            },
        )
    return candidates[0]


def read_image_resolution(path: Path) -> tuple[int, int]:
    """Return (width, height) using PNG/JPEG headers (stdlib only)."""
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _png_dimensions(path)
    if suffix in {".jpg", ".jpeg"}:
        return _jpeg_dimensions(path)
    raise ValidationAppError(
        f"Unsupported image format: {path.suffix}",
        code="RENDER_UNSUPPORTED_IMAGE",
        details={"path": str(path)},
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        header = fh.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationAppError(
            "Invalid PNG file.",
            code="RENDER_INVALID_IMAGE",
            details={"path": str(path)},
        )
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise ValidationAppError(
            "PNG has invalid dimensions.",
            code="RENDER_INVALID_IMAGE",
            details={"path": str(path), "width": width, "height": height},
        )
    return width, height


def _jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    index = 2
    while index < len(data) - 9:
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = (data[index + 3] << 8) + data[index + 4]
            width = (data[index + 5] << 8) + data[index + 6]
            if width > 0 and height > 0:
                return width, height
            break
        if marker in {0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9}:
            continue
        if index + 1 >= len(data):
            break
        segment_len = (data[index] << 8) + data[index + 1]
        index += max(segment_len, 2)
    raise ValidationAppError(
        "Could not read JPEG dimensions.",
        code="RENDER_INVALID_IMAGE",
        details={"path": str(path)},
    )


def generate_identical_frames(
    *,
    source_image: Path,
    frames_dir: Path,
    config: RenderConfig,
) -> int:
    """Write ``fps × duration`` identical frame files (legacy helper / tests)."""
    ext = config.frame_format.lower().lstrip(".")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob(f"*.{ext}"):
        old.unlink()

    expected = config.frame_count
    for index in range(1, expected + 1):
        dest = frames_dir / f"{index:06d}.{ext}"
        shutil.copy2(source_image, dest)

    written = sum(1 for _ in frames_dir.glob(f"*.{ext}"))
    if written != expected:
        raise ValidationAppError(
            "Frame count does not match fps × duration.",
            code="RENDER_FRAME_COUNT_MISMATCH",
            details={
                "expected": expected,
                "written": written,
                "fps": config.fps,
                "duration": config.duration_sec,
            },
        )
    return written


def render_frame(
    *,
    source_image: Path,
    viewport: Viewport,
    output_size: tuple[int, int],
    dest: Path,
) -> None:
    """Crop ``viewport`` from the source image and scale to ``output_size``.

    Viewport crop, even-pixel snap, and resize are done with Pillow (not fitz).
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise ExplainXError(
            "Pillow is required for camera frame rendering.",
            code="RENDER_DEPENDENCY_MISSING",
            details={"missing": "pillow"},
        ) from exc

    out_w, out_h = even_dimensions(int(output_size[0]), int(output_size[1]))
    if out_w <= 0 or out_h <= 0:
        raise ValidationAppError(
            "Output size must be positive.",
            code="CAMERA_INVALID_VIEWPORT",
            details={"output_size": output_size},
        )
    if viewport.width <= 0 or viewport.height <= 0:
        raise ValidationAppError(
            "Viewport clip has non-positive dimensions.",
            code="CAMERA_INVALID_VIEWPORT",
            details={"width": viewport.width, "height": viewport.height},
        )

    # Always reopen the ORIGINAL composed/source image — never crop a prior frame.
    with Image.open(source_image) as src:
        image = src.convert("RGB")
        img_w, img_h = image.size

        # Keep camera math in float; round once into a stable integer crop box.
        crop_w = max(1, int(round(float(viewport.width))))
        crop_h = max(1, int(round(float(viewport.height))))
        left = int(round(float(viewport.x)))
        top = int(round(float(viewport.y)))
        left = max(0, min(left, max(0, img_w - crop_w)))
        top = max(0, min(top, max(0, img_h - crop_h)))
        right = min(img_w, left + crop_w)
        bottom = min(img_h, top + crop_h)
        if right <= left or bottom <= top:
            raise ValidationAppError(
                "Viewport clip has non-positive dimensions.",
                code="CAMERA_INVALID_VIEWPORT",
                details={"left": left, "top": top, "right": right, "bottom": bottom},
            )

        image = image.crop((left, top, right, bottom))

        if image.size != (out_w, out_h):
            image = image.resize((out_w, out_h), Image.Resampling.LANCZOS)

        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest)


def generate_camera_frames_segment(
    *,
    source_image: Path,
    frames_dir: Path,
    fps: int,
    duration_sec: int,
    frame_format: str,
    camera: CameraService,
    output_size: tuple[int, int],
    frame_start_index: int,
) -> int:
    """Render one scene segment; frames are numbered from ``frame_start_index``."""
    ext = frame_format.lower().lstrip(".")
    expected = fps * duration_sec
    for local_index in range(expected):
        global_index = frame_start_index + local_index
        time_seconds = local_index / fps
        viewport = camera.get_viewport(time_seconds)
        scale = camera.scale_at_time(time_seconds)
        local_frame = local_index + 1

        # Temporary debug: confirm camera motion within each scene.
        if local_frame in {1, 45, 90} or local_frame == expected:
            print(f"Frame {local_frame}", flush=True)
            print(f"Scale: {scale:.3f}", flush=True)
            print("Viewport:", flush=True)
            print(f"x {viewport.x:.2f}", flush=True)
            print(f"y {viewport.y:.2f}", flush=True)
            print(f"width {viewport.width:.2f}", flush=True)
            print(f"height {viewport.height:.2f}", flush=True)

        dest = frames_dir / f"{global_index:06d}.{ext}"
        render_frame(
            source_image=source_image,
            viewport=viewport,
            output_size=output_size,
            dest=dest,
        )
    return expected


def generate_camera_frames(
    *,
    source_image: Path,
    frames_dir: Path,
    config: RenderConfig,
    camera: CameraService,
    output_size: tuple[int, int],
) -> int:
    """Render one frame per timestep using the camera viewport."""
    ext = config.frame_format.lower().lstrip(".")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob(f"*.{ext}"):
        old.unlink()

    expected = config.frame_count
    fps = config.fps
    for index in range(1, expected + 1):
        time_seconds = (index - 1) / fps
        viewport = camera.get_viewport(time_seconds)
        scale = camera.scale_at_time(time_seconds)

        # Temporary debug logging (every 100 frames + first/last).
        if index == 1 or index == expected or index % 100 == 0:
            print(f"Frame {index}", flush=True)
            print(f"Scale {scale:.3f}", flush=True)
            print("Viewport", flush=True)
            print(f"x {viewport.x:.2f}", flush=True)
            print(f"y {viewport.y:.2f}", flush=True)
            print(f"width {viewport.width:.2f}", flush=True)
            print(f"height {viewport.height:.2f}", flush=True)

        dest = frames_dir / f"{index:06d}.{ext}"
        render_frame(
            source_image=source_image,
            viewport=viewport,
            output_size=output_size,
            dest=dest,
        )

    written = sum(1 for _ in frames_dir.glob(f"*.{ext}"))
    if written != expected:
        raise ValidationAppError(
            "Frame count does not match fps × duration.",
            code="RENDER_FRAME_COUNT_MISMATCH",
            details={
                "expected": expected,
                "written": written,
                "fps": config.fps,
                "duration": config.duration_sec,
            },
        )
    return written
