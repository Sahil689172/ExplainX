"""Validate TeachingOutline structure and word-budget allocation."""

from __future__ import annotations

from app.core.errors import ValidationAppError
from app.features.input.schemas import RawContent
from app.features.outline.budget import WORD_BUDGET_TOLERANCE
from app.features.outline.schemas import (
    OUTLINE_SECTION_MAX,
    OUTLINE_SECTION_MIN,
    TeachingOutline,
)


class OutlineValidator:
    """Ensure outline is a valid lesson plan (never checks narration)."""

    def validate(
        self,
        outline: TeachingOutline,
        *,
        raw: RawContent | None = None,
    ) -> None:
        count = len(outline.sections)
        if count < OUTLINE_SECTION_MIN or count > OUTLINE_SECTION_MAX:
            raise ValidationAppError(
                f"TeachingOutline must have {OUTLINE_SECTION_MIN}–{OUTLINE_SECTION_MAX} sections.",
                code="OUTLINE_VALIDATION_ERROR",
                details={
                    "section_count": count,
                    "min": OUTLINE_SECTION_MIN,
                    "max": OUTLINE_SECTION_MAX,
                },
            )

        section_ids = [s.id for s in outline.sections]
        if len(set(section_ids)) != len(section_ids):
            raise ValidationAppError(
                "TeachingOutline section ids must be unique.",
                code="OUTLINE_VALIDATION_ERROR",
                details={"field": "sections.id"},
            )

        for section in outline.sections:
            if not section.title.strip():
                raise ValidationAppError(
                    "Teaching section title is required.",
                    code="OUTLINE_VALIDATION_ERROR",
                    details={"section_id": section.id, "field": "title"},
                )
            if not section.learning_objective.strip():
                raise ValidationAppError(
                    "Teaching section learning_objective is required.",
                    code="OUTLINE_VALIDATION_ERROR",
                    details={"section_id": section.id, "field": "learning_objective"},
                )
            if section.target_words < 1:
                raise ValidationAppError(
                    "Teaching section target_words must be positive.",
                    code="OUTLINE_VALIDATION_ERROR",
                    details={"section_id": section.id, "field": "target_words"},
                )
            if not section.key_concepts:
                raise ValidationAppError(
                    "Teaching section must include at least one key concept.",
                    code="OUTLINE_VALIDATION_ERROR",
                    details={"section_id": section.id, "field": "key_concepts"},
                )

        allocated = outline.allocated_words
        delta = abs(allocated - outline.total_target_words)
        if delta > WORD_BUDGET_TOLERANCE:
            raise ValidationAppError(
                "Allocated section target_words must match total_target_words "
                f"within ±{WORD_BUDGET_TOLERANCE}.",
                code="OUTLINE_VALIDATION_ERROR",
                details={
                    "total_target_words": outline.total_target_words,
                    "allocated_words": allocated,
                    "delta": delta,
                    "tolerance": WORD_BUDGET_TOLERANCE,
                },
            )

        if raw is not None and outline.content_id != raw.content_id:
            raise ValidationAppError(
                "TeachingOutline.content_id must match RawContent.content_id.",
                code="OUTLINE_VALIDATION_ERROR",
                details={
                    "outline_content_id": outline.content_id,
                    "raw_content_id": raw.content_id,
                },
            )
