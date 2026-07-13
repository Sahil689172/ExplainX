"""Minimal Piper TTS invocation (CLI subprocess)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.errors import ExplainXError, ValidationAppError


def synthesize_wav(
    text: str,
    *,
    executable: str,
    model: str,
    output_wav: Path,
) -> Path:
    """Run Piper and write a WAV file. Returns ``output_wav`` on success."""
    cleaned = text.strip()
    if not cleaned:
        raise ValidationAppError(
            "Narration text is empty; cannot synthesize speech.",
            code="VOICE_EMPTY_TEXT",
            details={"field": "text"},
        )
    exe = (executable or "").strip()
    model_path = (model or "").strip()
    if not exe:
        raise ValidationAppError(
            "PIPER_EXECUTABLE is not configured.",
            code="PIPER_NOT_CONFIGURED",
            details={"field": "piper_executable"},
        )
    if not model_path:
        raise ValidationAppError(
            "PIPER_MODEL is not configured.",
            code="PIPER_NOT_CONFIGURED",
            details={"field": "piper_model"},
        )
    if not Path(exe).is_file():
        raise ValidationAppError(
            f"Piper executable not found: {exe}",
            code="PIPER_NOT_FOUND",
            details={"piper_executable": exe},
        )
    if not Path(model_path).is_file():
        raise ValidationAppError(
            f"Piper model not found: {model_path}",
            code="PIPER_MODEL_NOT_FOUND",
            details={"piper_model": model_path},
        )

    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    if output_wav.exists():
        output_wav.unlink()

    cmd = [
        exe,
        "--model",
        model_path,
        "--output_file",
        str(output_wav),
    ]
    try:
        completed = subprocess.run(
            cmd,
            input=cleaned.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExplainXError(
            "Piper speech synthesis timed out.",
            code="PIPER_TIMEOUT",
            details={"timeout_sec": 600},
            retriable=True,
        ) from exc
    except OSError as exc:
        raise ExplainXError(
            f"Failed to start Piper: {exc}",
            code="PIPER_EXEC_ERROR",
            details={"piper_executable": exe},
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ExplainXError(
            "Piper speech synthesis failed.",
            code="PIPER_SYNTH_FAILED",
            details={
                "returncode": completed.returncode,
                "stderr": stderr[:2000],
            },
        )

    if not output_wav.is_file() or output_wav.stat().st_size <= 0:
        raise ExplainXError(
            "Piper did not produce a valid audio.wav file.",
            code="PIPER_OUTPUT_MISSING",
            details={"path": str(output_wav)},
        )
    return output_wav
