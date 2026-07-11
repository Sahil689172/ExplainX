"""ScriptGenerator interface — Ollama/LLM implementations plug in later."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.input.schemas import RawContent
from app.features.presentation.schemas import PresentationPlan
from app.features.script.schemas import EducationalScript


@runtime_checkable
class ScriptGenerator(Protocol):
    """Generate an EducationalScript from normalized RawContent.

    Optional ``PresentationPlan`` supplies title / concepts when available.
    Implementations must not require LLM in the placeholder path.
    """

    def generate(
        self,
        raw: RawContent,
        *,
        plan: PresentationPlan | None = None,
    ) -> EducationalScript: ...
