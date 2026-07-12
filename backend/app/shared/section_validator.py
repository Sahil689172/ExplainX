"""Validate per-section narration outputs (shared by generation + quality)."""

from __future__ import annotations

import re

from app.core.errors import ValidationAppError
from app.features.outline.schemas import TeachingSection
from app.features.script.metrics import count_words
from app.shared.section_output import SectionOutput

_UNSPEAKABLE = re.compile(r"(```|<html|<table\b)", re.IGNORECASE)


class SectionValidator:
    """Validate a single SectionOutput against its outline TeachingSection.

    MVP: ``target_words`` is prompt guidance only — word-count drift never fails
    section validation. Fail only on structural / empty narration issues.
    """

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
        elif count_words(output.narration) < 1:
            errors.append("Section narration must contain at least one word.")
        if not output.summary.strip():
            errors.append("Section summary is required for next-section context.")

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
        raise ValidationAppError(
            errors[0],
            code="SECTION_VALIDATION_ERROR",
            details={
                "section_id": expected.id,
                "index": index,
                "actual_words": words,
                "target_words": expected.target_words,
                "errors": errors,
            },
        )
