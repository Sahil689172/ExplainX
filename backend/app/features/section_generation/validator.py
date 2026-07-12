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

    def collect_errors(
        self,
        output: SectionOutput,
        *,
        expected: TeachingSection,
        index: int,
    ) -> list[str]:
        """Return validation error messages without raising."""
        errors: list[str] = []

        if output.outline_section_id != expected.id:
            errors.append(
                "Section output id does not match outline section id "
                f"(expected={expected.id}, actual={output.outline_section_id})."
            )
        if output.index != index:
            errors.append(
                f"Section output index mismatch (expected={index}, actual={output.index})."
            )
        if not output.narration.strip():
            errors.append("Section narration must be non-empty.")
        elif _UNSPEAKABLE.search(output.narration):
            errors.append("Section narration contains unspeakable formatting.")
        if not output.summary.strip():
            errors.append("Section summary is required for next-section context.")

        words = count_words(output.narration)
        if words < 1:
            errors.append("Section narration must contain at least one word.")
        else:
            target = max(expected.target_words, 1)
            low = max(1, int(target * WORD_COUNT_MIN_RATIO))
            high = max(low, int(target * WORD_COUNT_MAX_RATIO))
            if words < low or words > high:
                errors.append(
                    "Section narration word count is outside the allowed band "
                    f"for target_words (actual={words}, target={target}, "
                    f"min={low}, max={high})."
                )

        return errors

    def validate(
        self,
        output: SectionOutput,
        *,
        expected: TeachingSection,
        index: int,
    ) -> None:
        errors = self.collect_errors(output, expected=expected, index=index)
        if not errors:
            return

        words = count_words(output.narration)
        target = max(expected.target_words, 1)
        raise ValidationAppError(
            errors[0],
            code="SECTION_VALIDATION_ERROR",
            details={
                "section_id": expected.id,
                "index": index,
                "actual_words": words,
                "target_words": target,
                "errors": errors,
            },
        )
