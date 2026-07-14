"""EN→Indic translation via deep-translator GoogleTranslator."""

from __future__ import annotations

import re
from typing import Any

from app.core.errors import ExplainXError

SUPPORTED_TARGETS = frozenset({"hi", "te"})

# Google Translate free endpoint roughly caps around 5k chars per request.
_MAX_CHUNK_CHARS = 4500
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


class TranslationFailedError(ExplainXError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="TRANSLATION_FAILED",
            status_code=500,
            details=details,
            retriable=False,
        )


def _split_chunks(text: str) -> list[str]:
    """Split into sentence-sized pieces that stay under the API size limit."""
    sentences = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
    if not sentences:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > _MAX_CHUNK_CHARS:
            if current:
                chunks.append(current.strip())
                current = ""
            # Hard-split oversized sentences.
            for i in range(0, len(sentence), _MAX_CHUNK_CHARS):
                chunks.append(sentence[i : i + _MAX_CHUNK_CHARS])
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= _MAX_CHUNK_CHARS:
            current = candidate
        else:
            chunks.append(current.strip())
            current = sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


def translate_english_to(
    text: str,
    *,
    target_lang: str,
    model_id: str | None = None,  # unused; kept for call-site compatibility
) -> str:
    """Translate English text to Hindi (hi) or Telugu (te) via GoogleTranslator."""
    _ = model_id
    cleaned = (text or "").strip()
    if not cleaned:
        raise TranslationFailedError(
            "Cannot translate empty text.",
            details={"field": "text"},
        )

    code = (target_lang or "").strip().lower()[:2]
    if code not in SUPPORTED_TARGETS:
        raise TranslationFailedError(
            f"Unsupported translation target: {target_lang!r}. Use hi or te.",
            details={"target_lang": target_lang, "supported": sorted(SUPPORTED_TARGETS)},
        )

    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:
        raise TranslationFailedError(
            "deep-translator is required. Install with: pip install deep-translator",
            details={"missing": str(exc)},
        ) from exc

    try:
        translator = GoogleTranslator(source="en", target=code)
        parts: list[str] = []
        for chunk in _split_chunks(cleaned):
            translated = translator.translate(chunk)
            if translated is None or not str(translated).strip():
                raise TranslationFailedError(
                    "GoogleTranslator returned empty output.",
                    details={"language": code},
                )
            parts.append(str(translated).strip())
    except TranslationFailedError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TranslationFailedError(
            "Google translation failed.",
            details={"error": str(exc), "target_lang": code},
        ) from exc

    return " ".join(parts).strip()
