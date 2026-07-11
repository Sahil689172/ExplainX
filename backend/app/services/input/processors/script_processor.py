"""Custom narration/script text → RawContent (no AI)."""

from __future__ import annotations

import re

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.models.artifacts.raw_content import RawContent, RawContentSection
from app.services.input.processors.base import (
    BaseInputProcessor,
    ProcessorContext,
    sha256_text,
)


class ScriptProcessor(BaseInputProcessor):
    """Treats user-authored script as first-class source content."""

    source_type = SourceType.SCRIPT

    def process(self, ctx: ProcessorContext) -> RawContent:
        script = (ctx.script_text or "").strip()
        if len(script) < 10:
            raise ValidationAppError(
                "Script must be at least 10 characters.",
                code="VALIDATION_ERROR",
                details={"field": "script"},
            )
        if len(script) > 200_000:
            raise ValidationAppError(
                "Script exceeds the maximum allowed length.",
                code="VALIDATION_ERROR",
                details={"field": "script", "max_chars": 200_000},
            )

        blocks = [b.strip() for b in re.split(r"\n\s*\n", script) if b.strip()]
        if not blocks:
            raise ValidationAppError(
                "Script produced no extractable text.",
                code="PARSER_EMPTY_CONTENT",
                details={"source_type": "script"},
            )

        title = None
        if ctx.extra.get("title"):
            title = str(ctx.extra["title"]).strip() or None

        sections: list[RawContentSection] = []
        for index, block in enumerate(blocks, start=1):
            section_title = title if index == 1 else None
            sections.append(
                RawContentSection(
                    id=f"section-{index}",
                    text=block,
                    order=index,
                    title=section_title,
                )
            )

        return self._build(
            project_id=ctx.project_id,
            sections=sections,
            warnings=[],
            source_path=ctx.source_path_relative,
            source_hash=ctx.source_hash or sha256_text(script),
            metadata={
                "input_kind": "script",
                "language_hint": ctx.language_hint,
                "title": title,
                "paragraph_count": len(blocks),
            },
            page_count=0,
        )
