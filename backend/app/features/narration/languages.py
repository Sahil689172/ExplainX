"""Output language helpers (en / hi / te).

Script generation is always English. These codes are for requested output
language (project target) and Piper / translation targets only.
"""

from __future__ import annotations

from app.core.errors import ValidationAppError

# Canonical script language — always English.
CANONICAL_SCRIPT_LANGUAGE = "en"

# Requested TTS / translation output languages.
SUPPORTED_OUTPUT_LANGUAGES = ("en", "hi", "te")

# Backwards-compatible alias used by CLI / Piper.
SUPPORTED_NARRATION_LANGUAGES = SUPPORTED_OUTPUT_LANGUAGES

_LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}


def normalize_output_language(value: str | None, *, default: str = "en") -> str:
    """Normalize to a supported two-letter output language code."""
    raw = (value or default or "en").strip().lower()
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    code = raw[:2] if len(raw) >= 2 else default
    if code not in SUPPORTED_OUTPUT_LANGUAGES:
        raise ValidationAppError(
            f"Unsupported output language: {value!r}. Use en, hi, or te.",
            code="LANGUAGE_NOT_SUPPORTED",
            details={
                "language": value,
                "supported_languages": list(SUPPORTED_OUTPUT_LANGUAGES),
            },
        )
    return code


# Alias kept for existing imports.
normalize_narration_language = normalize_output_language


def language_label(code: str) -> str:
    return _LANGUAGE_LABELS.get(normalize_output_language(code), code)


def log_script_language(*, generated: str = CANONICAL_SCRIPT_LANGUAGE) -> None:
    print("[Script]", flush=True)
    print(f"Language Generated : {language_label(generated)}", flush=True)
