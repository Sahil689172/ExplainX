"""Topic → EducationalScript (placeholder research + narration)."""

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


class TopicContentProcessor:
    """Placeholder research outline + teaching narration for topic inputs."""

    source_type = SourceType.TOPIC

    def __init__(self, generator: ContentGenerator | None = None) -> None:
        self._generator = generator or PlaceholderContentGenerator()

    def process(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        plan: PresentationPlan | None = None,
        pdf_path: Path | None = None,  # noqa: ARG002 — unused for topic
    ) -> EducationalScript:
        title = resolve_title(raw, plan)
        topic = " ".join(raw.text.split()).strip() or title

        # Placeholder "research": expand the topic into a fixed teaching outline.
        research_sections = [
            RawContentSection(
                id="topic-intro",
                order=1,
                title="Introduction",
                text=(
                    f"Today we will learn about {title}. "
                    f"{topic} is an important idea to understand clearly."
                ),
            ),
            RawContentSection(
                id="topic-core",
                order=2,
                title="Core Idea",
                text=(
                    f"At its core, {title} means: {topic}. "
                    "We will break this into simple steps so it is easy to remember."
                ),
            ),
            RawContentSection(
                id="topic-summary",
                order=3,
                title="Summary",
                text=(
                    f"To summarize, {title} helps us reason carefully. "
                    "Remember the main idea and practice applying it."
                ),
            ),
        ]

        return self._generator.generate(
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=SourceType.TOPIC,
            title=title,
            language=resolve_language(raw, plan),
            sections=[
                s.model_copy(update={"text": improve_readability(s.text)})
                for s in research_sections
            ],
            concepts=resolve_concepts(raw, plan),
            target_duration_sec=target_duration_sec,
            warnings=list(raw.warnings),
            metadata={
                "processor": "topic_content_v1",
                "used_presentation_plan": plan is not None,
                "plan_id": plan.plan_id if plan else None,
                "research_mode": "placeholder",
            },
        )
