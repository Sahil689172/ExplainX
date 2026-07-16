"""FFmpeg export for static-frame sequences."""

from __future__ import annotations

import shutil
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
    if not list(frames_dir.glob(f"*.{ext}")):
        raise ValidationAppError(
            "No frames found for FFmpeg export.",
            code="RENDER_NO_FRAMES",
            details={"frames_dir": str(frames_dir)},
        )

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
