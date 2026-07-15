"""Language-agnostic TTS text cleanup (does not rewrite wording)."""

from __future__ import annotations

import re
import unicodedata

_MARKDOWN_CHARS = re.compile(r"[*_#`~>|]")
_MULTI_SPACE = re.compile(r"[ \t\f\v]+")
_MULTI_NL = re.compile(r"\n{3,}")
_DUP_PUNCT = re.compile(r"([.!?।॥,;:…])\1+")
# Common invisible / format controls excluding normal whitespace newlines/tabs.
_INVISIBLE = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\u00ad"
    r"\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)


def clean_speech_text(text: str) -> str:
    """Strip markdown markers, invisible unicode, and normalize spacing/punctuation.

    Does not change wording beyond removing formatting noise.
    """
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFC", text)
    cleaned = _INVISIBLE.sub("", cleaned)
    cleaned = _MARKDOWN_CHARS.sub("", cleaned)
    # Soft-remove markdown-style ATFs if whole line is a heading marker remnant.
    lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        lines.append(stripped)
    cleaned = "\n".join(lines)
    cleaned = _DUP_PUNCT.sub(r"\1", cleaned)
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    cleaned = _MULTI_NL.sub("\n\n", cleaned)
    return cleaned.strip()
