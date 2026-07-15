"""Central Piper preferred-voice mapping (language → voice stem)."""

from __future__ import annotations

# Preferred ONNX stem (without .onnx) per language.
# Future languages: add one entry here.
PREFERRED_VOICES: dict[str, str] = {
    "en": "en_US-lessac-medium",
    "hi": "hi_IN-pratham-medium",
    "te": "te_IN-venkatesh-medium",
}


def preferred_voice_stem(language: str) -> str | None:
    code = (language or "en").strip().lower()[:2]
    return PREFERRED_VOICES.get(code)
