"""Validate EducationalScript invariants and V1 duration/word bands."""

from __future__ import annotations

import re

from app.core.errors import ValidationAppError
from app.features.input.schemas import RawContent
from app.features.script.durations import (
    V1_MAX_DURATION_SEC,
    V1_MAX_WORDS,
    V1_MIN_DURATION_SEC,
    V1_MIN_WORDS,
)
from app.features.script.metrics import ScriptMetricsCalculator, count_words
from app.features.script.schemas import EducationalScript

_UNSPEAKABLE = re.compile(r"(```|<html|<table\b)", re.IGNORECASE)


class ScriptValidator:
    """Validate scripts using deterministically calculated metrics only."""

    def __init__(self, *, calculator: ScriptMetricsCalculator | None = None) -> None:
        self._calculator = calculator or ScriptMetricsCalculator()

    def validate(self, script: EducationalScript, *, raw: RawContent | None = None) -> None:
        if not script.teaching_sections:
            raise ValidationAppError(
                "EducationalScript must include at least one teaching section.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "teaching_sections"},
            )

        if not script.summary.strip():
            raise ValidationAppError(
                "EducationalScript.summary is required.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "summary"},
            )

        section_ids = [s.id for s in script.teaching_sections]
        if len(set(section_ids)) != len(section_ids):
            raise ValidationAppError(
                "teaching_sections.id values must be unique.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "teaching_sections.id"},
            )

        for section in script.teaching_sections:
            if _UNSPEAKABLE.search(section.narration):
                raise ValidationAppError(
                    "teaching section narration contains unspeakable formatting.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"section_id": section.id},
                )
            words = count_words(section.narration)
            if words <= 0:
                raise ValidationAppError(
                    "teaching section narration must contain at least one word.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"section_id": section.id},
                )

        # Always validate calculated values — never trust generator-supplied numbers.
        metrics = self._calculator.compute(script)
        if metrics.total_duration_sec < V1_MIN_DURATION_SEC:
            raise ValidationAppError(
                f"Estimated duration must be at least {V1_MIN_DURATION_SEC} seconds.",
                code="SCRIPT_VALIDATION_ERROR",
                details={
                    "estimated_duration_sec": metrics.total_duration_sec,
                    "min": V1_MIN_DURATION_SEC,
                },
            )
        if metrics.total_duration_sec > V1_MAX_DURATION_SEC:
            raise ValidationAppError(
                f"Estimated duration must be at most {V1_MAX_DURATION_SEC} seconds.",
                code="SCRIPT_VALIDATION_ERROR",
                details={
                    "estimated_duration_sec": metrics.total_duration_sec,
                    "max": V1_MAX_DURATION_SEC,
                },
            )
        if metrics.total_words < V1_MIN_WORDS:
            raise ValidationAppError(
                f"Total words must be at least {V1_MIN_WORDS}.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"total_words": metrics.total_words, "min": V1_MIN_WORDS},
            )
        if metrics.total_words > V1_MAX_WORDS:
            raise ValidationAppError(
                f"Total words must be at most {V1_MAX_WORDS}.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"total_words": metrics.total_words, "max": V1_MAX_WORDS},
            )

        if raw is not None and script.content_id != raw.content_id:
            raise ValidationAppError(
                "EducationalScript.content_id must match RawContent.content_id.",
                code="SCRIPT_VALIDATION_ERROR",
                details={
                    "script_content_id": script.content_id,
                    "raw_content_id": raw.content_id,
                },
            )
