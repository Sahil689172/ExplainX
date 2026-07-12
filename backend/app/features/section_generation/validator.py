"""Validate per-section narration outputs (Phase 3.8)."""

from __future__ import annotations

import re

from app.core.errors import ValidationAppError
from app.features.outline.schemas import TeachingSection
from app.features.script.metrics import count_words
from app.features.section_generation.schemas import SectionOutput

_UNSPEAKABLE = re.compile(r"(```|<html|<table\b)", re.IGNORECASE)

# Allow LLM drift around the outline target; merger + ScriptValidator own the band.
WORD_COUNT_MIN_RATIO = 0.45
WORD_COUNT_MAX_RATIO = 1.60


class SectionValidator:
    """Validate a single SectionOutput against its outline TeachingSection."""

    def validate(
        self,
        output: SectionOutput,
        *,
        expected: TeachingSection,
        index: int,
    ) -> None:
        if output.outline_section_id != expected.id:
            raise ValidationAppError(
                "Section output id does not match outline section id.",
                code="SECTION_VALIDATION_ERROR",
                details={
                    "expected_id": expected.id,
                    "actual_id": output.outline_section_id,
                    "index": index,
                },
            )
        if output.index != index:
            raise ValidationAppError(
                "Section output index mismatch.",
                code="SECTION_VALIDATION_ERROR",
                details={"expected_index": index, "actual_index": output.index},
            )
        if not output.narration.strip():
            raise ValidationAppError(
                "Section narration must be non-empty.",
                code="SECTION_VALIDATION_ERROR",
                details={"section_id": expected.id, "index": index},
            )
        if _UNSPEAKABLE.search(output.narration):
            raise ValidationAppError(
                "Section narration contains unspeakable formatting.",
                code="SECTION_VALIDATION_ERROR",
                details={"section_id": expected.id, "index": index},
            )
        if not output.summary.strip():
            raise ValidationAppError(
                "Section summary is required for next-section context.",
                code="SECTION_VALIDATION_ERROR",
                details={"section_id": expected.id, "index": index},
            )

        words = count_words(output.narration)
        if words < 1:
            raise ValidationAppError(
                "Section narration must contain at least one word.",
                code="SECTION_VALIDATION_ERROR",
                details={"section_id": expected.id, "index": index},
            )

        target = max(expected.target_words, 1)
        low = max(1, int(target * WORD_COUNT_MIN_RATIO))
        high = max(low, int(target * WORD_COUNT_MAX_RATIO))
        if words < low or words > high:
            raise ValidationAppError(
                "Section narration word count is outside the allowed band for target_words.",
                code="SECTION_VALIDATION_ERROR",
                details={
                    "section_id": expected.id,
                    "index": index,
                    "actual_words": words,
                    "target_words": target,
                    "min_words": low,
                    "max_words": high,
                },
            )
