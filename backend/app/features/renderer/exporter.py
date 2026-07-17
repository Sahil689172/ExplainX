"""FFmpeg export for static-frame sequences."""

from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path

from app.core.errors import ExplainXError, ValidationAppError
from app.features.renderer.schemas import RenderConfig

_REPO_ROOT = Path(__file__).resolve().parents[4]


def resolve_ffmpeg_executable(
    configured: str,
    *,
    repo_root: Path | None = None,
) -> str:
    """Resolve FFmpeg binary from settings, PATH, or common install locations."""
    root = repo_root or _REPO_ROOT
    raw = (configured or "").strip()
    if raw:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        if candidate.is_file():
            return str(candidate)
        found = shutil.which(raw)
        if found:
            return found

    for relative in (
        Path("data") / "bin" / "ffmpeg" / "ffmpeg.exe",
        Path("data") / "bin" / "ffmpeg" / "ffmpeg",
        Path("tools") / "ffmpeg" / "ffmpeg.exe",
        Path("ffmpeg") / "ffmpeg.exe",
    ):
        candidate = (root / relative).resolve()
        if candidate.is_file():
            return str(candidate)

    for name in ("ffmpeg.exe", "ffmpeg"):
        found = shutil.which(name)
        if found:
            return found

    raise ValidationAppError(
        "FFmpeg is not installed or not on PATH. "
        "Install FFmpeg and ensure it is available.",
        code="FFMPEG_NOT_CONFIGURED",
        details={"field": "ffmpeg_executable"},
    )


def _png_frame_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        header = fh.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationAppError(
            f"Invalid PNG frame: {path.name}",
            code="RENDER_INVALID_FRAME",
            details={"path": str(path)},
        )
    return struct.unpack(">II", header[16:24])


def _jpeg_frame_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    index = 2
    while index < len(data) - 9:
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
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
        f"Could not read JPEG frame size: {path.name}",
        code="RENDER_INVALID_FRAME",
        details={"path": str(path)},
    )


def read_frame_size(path: Path) -> tuple[int, int]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _png_frame_size(path)
    if suffix in {".jpg", ".jpeg"}:
        return _jpeg_frame_size(path)
    raise ValidationAppError(
        f"Unsupported frame format: {path.suffix}",
        code="RENDER_UNSUPPORTED_IMAGE",
        details={"path": str(path)},
    )


def validate_frame_sequence(frames_dir: Path, *, frame_format: str) -> tuple[int, int]:
    """Ensure every frame shares identical even dimensions (libx264-safe)."""
    ext = frame_format.lower().lstrip(".")
    frames = sorted(frames_dir.glob(f"*.{ext}"))
    if not frames:
        raise ValidationAppError(
            "No frames found for FFmpeg export.",
            code="RENDER_NO_FRAMES",
            details={"frames_dir": str(frames_dir)},
        )

    width, height = read_frame_size(frames[0])
    if width % 2 != 0 or height % 2 != 0:
        raise ValidationAppError(
            "Frame dimensions must be even for libx264.",
            code="RENDER_ODD_FRAME_SIZE",
            details={"width": width, "height": height, "frame": frames[0].name},
        )

    for frame in frames[1:]:
        fw, fh = read_frame_size(frame)
        if (fw, fh) != (width, height):
            raise ValidationAppError(
                "Frame sequence has inconsistent dimensions.",
                code="RENDER_FRAME_SIZE_MISMATCH",
                details={
                    "expected": [width, height],
                    "actual": [fw, fh],
                    "frame": frame.name,
                },
            )

    print("Frame Size:", flush=True)
    print(f"{width} x {height}", flush=True)
    return width, height


def export_video(
    *,
    frames_dir: Path,
    output_video: Path,
    config: RenderConfig,
    ffmpeg_executable: str,
) -> Path:
    """Encode numbered frames into ``video.mp4`` via FFmpeg."""
    ext = config.frame_format.lower().lstrip(".")
    pattern = str(frames_dir / f"%06d.{ext}")
    validate_frame_sequence(frames_dir, frame_format=ext)

    output_video.parent.mkdir(parents=True, exist_ok=True)
    if output_video.exists():
        output_video.unlink()

    cmd = [
        ffmpeg_executable,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        str(config.fps),
        "-i",
        pattern,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_video),
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExplainXError(
            "FFmpeg video export timed out.",
            code="FFMPEG_TIMEOUT",
            details={"timeout_sec": 600},
            retriable=True,
        ) from exc
    except OSError as exc:
        raise ExplainXError(
            f"Failed to start FFmpeg: {exc}",
            code="FFMPEG_EXEC_ERROR",
            details={"ffmpeg_executable": ffmpeg_executable},
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ExplainXError(
            "FFmpeg video export failed.",
            code="FFMPEG_EXPORT_FAILED",
            details={
                "returncode": completed.returncode,
                "stderr": stderr[:2000],
            },
        )

    if not output_video.is_file() or output_video.stat().st_size <= 0:
        raise ExplainXError(
            "FFmpeg did not produce a valid video.mp4 file.",
            code="RENDER_OUTPUT_MISSING",
            details={"path": str(output_video)},
        )
    return output_video
