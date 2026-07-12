"""Custom script → EducationalScript (preserve intent, improve readability)."""

from __future__ import annotations

from pathlib import Path

from app.core.enums import SourceType
from app.features.input.schemas import RawContent, RawContentSection
from app.features.presentation.schemas import PresentationPlan
from app.features.script.generator import PlaceholderContentGenerator
from app.features.script.processors.common import (
    improve_readability,
    resolve_concepts,
    resolve_language,
    resolve_title,
)
from app.features.script.protocols import ContentGenerator
from app.features.script.schemas import EducationalScript


class ScriptContentProcessor:
    """Keep author wording; normalize readability only."""

    source_type = SourceType.SCRIPT

    def __init__(self, generator: ContentGenerator | None = None) -> None:
        self._generator = generator or PlaceholderContentGenerator()

    def process(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        plan: PresentationPlan | None = None,
        pdf_path: Path | None = None,  # noqa: ARG002
    ) -> EducationalScript:
        title = resolve_title(raw, plan)
        source_sections = raw.sections or [
            RawContentSection(id="script-1", text=raw.text, order=1, title=title)
        ]
        improved = [
            section.model_copy(update={"text": improve_readability(section.text)})
            for section in source_sections
            if section.text.strip()
        ]
        if not improved:
            improved = [
                RawContentSection(
                    id="script-1",
                    text=improve_readability(raw.text or title),
                    order=1,
                    title=title,
                )
            ]

        return self._generator.generate(
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=SourceType.SCRIPT,
            title=title,
            language=resolve_language(raw, plan),
            sections=improved,
            concepts=resolve_concepts(raw, plan),
            target_duration_sec=target_duration_sec,
            warnings=list(raw.warnings),
            metadata={
                "processor": "script_content_v1",
                "used_presentation_plan": plan is not None,
                "plan_id": plan.plan_id if plan else None,
                "preserve_intent": True,
            },
        )
