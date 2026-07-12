"""Phase 3 content generation + processor protocols (Ollama-swappable)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.enums import SourceType
from app.features.input.schemas import RawContent, RawContentSection
from app.features.presentation.schemas import PresentationPlan
from app.features.script.schemas import EducationalScript, ScriptConcept


@runtime_checkable
class ContentGenerator(Protocol):
    """Turn prepared narration material into EducationalScript.

    ``PlaceholderContentGenerator`` is deterministic (no LLM).
    ``OllamaContentGenerator`` is the default ContentGenerator in Phase 3.5.
    """

    def generate(
        self,
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        title: str,
        language: str,
        sections: list[RawContentSection],
        concepts: list[ScriptConcept],
        target_duration_sec: int,
        warnings: list[str] | None = None,
        metadata: dict | None = None,
    ) -> EducationalScript: ...


@runtime_checkable
class ContentProcessor(Protocol):
    """Input-specific path that yields a common EducationalScript."""

    source_type: SourceType

    def process(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        plan: PresentationPlan | None = None,
        pdf_path: Path | None = None,
    ) -> EducationalScript: ...


@runtime_checkable
class ScriptGenerator(Protocol):
    """Legacy RawContent → EducationalScript facade (tests / older callers)."""

    def generate(
        self,
        raw: RawContent,
        *,
        plan: PresentationPlan | None = None,
        target_duration_sec: int = 60,
    ) -> EducationalScript: ...
