"""NarrationGenerator protocol — RawContent → continuous narration text."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.input.schemas import RawContent
from app.features.narration.schemas import NarrationDocument


@runtime_checkable
class NarrationGenerator(Protocol):
    """Produce continuous spoken narration (no sections / JSON structure)."""

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        repair_hint: str | None = None,
    ) -> NarrationDocument: ...
