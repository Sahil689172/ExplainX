"""Translation provider protocol (offline only)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TranslationProvider(Protocol):
    """Translate English narration text into a target language."""

    @property
    def name(self) -> str:
        """Human-readable provider name for logs."""
        ...

    def translate(self, text: str, *, target_lang: str) -> str:
        """Return translated text for ``target_lang`` (two-letter code)."""
        ...

    def supports(self, target_lang: str) -> bool:
        """Return True when this provider can handle ``target_lang``."""
        ...
