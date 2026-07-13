"""Normalize continuous narration text (no structural rewriting)."""

from __future__ import annotations

import re

from app.features.script.processors.common import improve_readability

_FENCE_RE = re.compile(r"^```(?:\w+)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_BULLET_LINE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


def strip_llm_wrappers(text: str) -> str:
    """Remove accidental markdown fences / leading labels from LLM output."""
    cleaned = text.strip()
    cleaned = _FENCE_RE.sub("", cleaned).strip()
    # Drop a leading JSON-ish wrapper if the model ignored instructions.
    if cleaned.startswith("{") and '"narration"' in cleaned[:200]:
        start = cleaned.find('"narration"')
        if start >= 0:
            colon = cleaned.find(":", start)
            if colon >= 0:
                rest = cleaned[colon + 1 :].strip()
                if rest.startswith('"'):
                    # naive extract of first string value
                    end = rest.find('"', 1)
                    if end > 1:
                        return rest[1:end].replace("\\n", "\n").strip()
    cleaned = _BULLET_LINE.sub("", cleaned)
    return " ".join(cleaned.split()).strip() if "\n" not in cleaned else cleaned.strip()


def normalize_author_script(text: str) -> str:
    """Whitespace/punctuation only — do not rewrite meaning."""
    return improve_readability(text)
