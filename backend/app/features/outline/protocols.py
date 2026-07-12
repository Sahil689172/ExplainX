"""OutlineGenerator protocol — swappable Placeholder / Ollama. Phase 3.7."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.input.schemas import RawContent
from app.features.outline.schemas import TeachingOutline


@runtime_checkable
class OutlineGenerator(Protocol):
    """Produce a TeachingOutline lesson plan from RawContent (no narration)."""

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        total_target_words: int,
    ) -> TeachingOutline: ...
