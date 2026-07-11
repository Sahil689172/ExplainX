"""Topic string → RawContent (no AI)."""

from __future__ import annotations

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.features.input.providers.base import (
    BaseInputProcessor,
    ProcessorContext,
    sha256_text,
)
from app.features.input.schemas import RawContent, RawContentSection


class TopicProcessor(BaseInputProcessor):
    source_type = SourceType.TOPIC

    def process(self, ctx: ProcessorContext) -> RawContent:
        topic = (ctx.topic or "").strip()
        if len(topic) < 3:
            raise ValidationAppError(
                "Topic must be at least 3 characters.",
                code="VALIDATION_ERROR",
                details={"field": "topic"},
            )
        if len(topic) > 500:
            raise ValidationAppError(
                "Topic must be at most 500 characters.",
                code="VALIDATION_ERROR",
                details={"field": "topic"},
            )

        sections = [
            RawContentSection(id="section-1", text=topic, order=1, title="Topic"),
        ]
        return self._build(
            project_id=ctx.project_id,
            sections=sections,
            warnings=[],
            source_path=ctx.source_path_relative,
            source_hash=ctx.source_hash or sha256_text(topic),
            metadata={
                "input_kind": "topic",
                "language_hint": ctx.language_hint,
                "raw_document_id": None,  # filled by service with content_id
            },
            page_count=0,
        )
