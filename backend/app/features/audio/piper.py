"""Minimal Piper TTS invocation with multilingual voice discovery."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import ExplainXError, ValidationAppError

SUPPORTED_LANGUAGES = ("en", "hi", "te")
_DOWNLOAD_SUFFIX = re.compile(r" \(\d+\)$")


@dataclass(frozen=True, slots=True)
class PiperVoice:
    """Discovered Piper voice model for a language."""

    language: str
    name: str
    model_path: Path
    config_path: Path | None


def resolve_voices_dir(voices_dir: str, *, repo_root: Path | None = None) -> Path:
    """Resolve PIPER_VOICES_DIR to an absolute path."""
    raw = (voices_dir or "").strip()
    if not raw:
        raise ValidationAppError(
            "PIPER_VOICES_DIR is not configured.",
            code="PIPER_NOT_CONFIGURED",
            details={"field": "piper_voices_dir"},
        )
    path = Path(raw)
    if not path.is_absolute():
        root = repo_root or Path(__file__).resolve().parents[4]
        path = root / path
    return path.resolve()


def resolve_piper_executable(
    configured: str,
    *,
    repo_root: Path | None = None,
) -> str:
    """Resolve Piper binary from settings, PATH, or common install locations."""
    root = repo_root or Path(__file__).resolve().parents[4]
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
        Path("data") / "bin" / "piper" / "piper.exe",
        Path("data") / "models" / "piper" / "piper.exe",
        Path("tools") / "piper" / "piper.exe",
        Path("piper") / "piper.exe",
    ):
        candidate = (root / relative).resolve()
        if candidate.is_file():
            return str(candidate)

    for name in ("piper.exe", "piper"):
        found = shutil.which(name)
        if found:
            return found

    raise ValidationAppError(
        "PIPER_EXECUTABLE is not configured and piper.exe was not found. "
        "Set PIPER_EXECUTABLE in .env to your piper.exe path.",
        code="PIPER_NOT_CONFIGURED",
        details={"field": "piper_executable"},
    )


def normalize_voice_filenames(lang_dir: Path) -> None:
    """Rename Chrome-style duplicate downloads to Piper's expected names.

    Examples:
      ``en_US-lessac-medium (1).onnx`` → ``en_US-lessac-medium.onnx``
      ``en_US-lessac-medium.onnx (1).json`` → ``en_US-lessac-medium.onnx.json``
    """
    if not lang_dir.is_dir():
        return

    # Fix ``*.onnx (N).json`` first so stems stay consistent.
    for path in sorted(lang_dir.glob("*.json")):
        name = path.name
        match = re.match(r"^(.+\.onnx) \(\d+\)\.json$", name)
        if not match:
            continue
        dest = lang_dir / f"{match.group(1)}.json"
        if dest.exists() and dest.resolve() != path.resolve():
            path.unlink()
            continue
        if dest.resolve() != path.resolve():
            path.rename(dest)

    for path in sorted(lang_dir.glob("*.onnx")):
        stem = path.stem
        cleaned = _DOWNLOAD_SUFFIX.sub("", stem).strip()
        if cleaned == stem:
            continue
        dest = lang_dir / f"{cleaned}.onnx"
        if dest.exists() and dest.resolve() != path.resolve():
            path.unlink()
            continue
        if dest.resolve() != path.resolve():
            path.rename(dest)


def _config_for_model(model_path: Path) -> Path | None:
    """Locate the JSON config Piper expects beside the ONNX model."""
    primary = Path(str(model_path) + ".json")
    if primary.is_file():
        return primary
    # Legacy Chrome misname already normalized; keep a soft fallback.
    alt = model_path.parent / f"{model_path.stem}.onnx.json"
    if alt.is_file():
        return alt
    return None


def discover_voice(
    voices_dir: Path,
    language: str,
    *,
    preferred_stem: str | None = None,
) -> PiperVoice:
    """Find a Piper voice under a language folder (prefer ``preferred_stem``)."""
    lang = (language or "").strip().lower()
    if len(lang) > 2 and "-" in lang:
        lang = lang.split("-", 1)[0]
    lang = lang[:2]

    if lang not in SUPPORTED_LANGUAGES:
        supported = "\n".join(SUPPORTED_LANGUAGES)
        raise ValidationAppError(
            f"Language not supported: {language!r}.\n\nSupported languages:\n{supported}",
            code="LANGUAGE_NOT_SUPPORTED",
            details={
                "language": language,
                "supported_languages": list(SUPPORTED_LANGUAGES),
            },
        )

    lang_dir = voices_dir / lang
    if not lang_dir.is_dir():
        supported = "\n".join(SUPPORTED_LANGUAGES)
        raise ValidationAppError(
            f"Language folder does not exist: {lang}\n\nSupported languages:\n{supported}",
            code="LANGUAGE_NOT_SUPPORTED",
            details={
                "language": lang,
                "supported_languages": list(SUPPORTED_LANGUAGES),
                "expected_path": str(lang_dir),
            },
        )

    normalize_voice_filenames(lang_dir)

    onnx_files = sorted(
        lang_dir.glob("*.onnx"),
        key=lambda p: (1 if " (" in p.stem else 0, p.name.lower()),
    )
    if not onnx_files:
        raise ValidationAppError(
            f"No ONNX voice model found for language: {lang}",
            code="VOICE_MODEL_NOT_FOUND",
            details={"language": lang, "voices_dir": str(lang_dir)},
        )

    model_path = onnx_files[0]
    if preferred_stem:
        preferred = preferred_stem.strip()
        for candidate in onnx_files:
            if candidate.stem == preferred or preferred in candidate.stem:
                model_path = candidate
                break

    config_path = _config_for_model(model_path)

    return PiperVoice(
        language=lang,
        name=model_path.stem,
        model_path=model_path,
        config_path=config_path,
    )


def log_audio_selection(*, language: str, voice: str) -> None:
    """Print the MVP audio selection banner."""
    print("[Audio]", flush=True)
    print(f"Language : {language}", flush=True)
    print(f"Voice : {voice}", flush=True)
    print("Provider : Piper", flush=True)


def synthesize_wav(
    text: str,
    *,
    executable: str,
    model: str,
    output_wav: Path,
    config: str | None = None,
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
    if not exe:
        raise ValidationAppError(
            "PIPER_EXECUTABLE is not configured.",
            code="PIPER_NOT_CONFIGURED",
            details={"field": "piper_executable"},
        )
    if not model:
        raise ValidationAppError(
            "No Piper voice model path provided.",
            code="VOICE_MODEL_NOT_FOUND",
            details={"field": "piper_model"},
        )
    if not Path(exe).is_file():
        raise ValidationAppError(
            f"Piper executable not found: {exe}",
            code="PIPER_NOT_FOUND",
            details={"piper_executable": exe},
        )
    model_path = Path(model)
    if not model_path.is_file():
        raise ValidationAppError(
            f"No ONNX voice model found: {model_path}",
            code="VOICE_MODEL_NOT_FOUND",
            details={"piper_model": str(model_path)},
        )

    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    if output_wav.exists():
        output_wav.unlink()

    cmd = [
        exe,
        "--model",
        str(model_path),
        "--output_file",
        str(output_wav),
    ]
    if config and Path(config).is_file():
        cmd.extend(["--config", str(config)])

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
            "Piper did not produce a valid WAV file.",
            code="PIPER_OUTPUT_MISSING",
            details={"path": str(output_wav)},
        )
    return output_wav
