"""Validate EducationalScript invariants for MVP (stable pipeline first)."""

from __future__ import annotations

import re

from app.core.errors import ValidationAppError
from app.features.input.schemas import RawContent
from app.features.script.durations import (
    SCRIPT_MAX_DURATION_SEC,
    SCRIPT_MIN_DURATION_SEC,
)
from app.features.script.metrics import ScriptMetricsCalculator, count_words
from app.features.script.schemas import EducationalScript

_UNSPEAKABLE = re.compile(r"(```|<html|<table\b)", re.IGNORECASE)


class ScriptValidator:
    """Validate scripts using deterministically calculated metrics only.

    MVP hard rules:
    - estimated duration within [min, max] seconds (default 60–300)
    - at least one teaching section
    - no empty narration
    - no duplicate section IDs

    Word counts are calculated for reporting — they do not fail validation.
    """

    def __init__(
        self,
        *,
        calculator: ScriptMetricsCalculator | None = None,
        min_duration_sec: int = SCRIPT_MIN_DURATION_SEC,
        max_duration_sec: int = SCRIPT_MAX_DURATION_SEC,
    ) -> None:
        self._calculator = calculator or ScriptMetricsCalculator()
        self._min_duration_sec = min_duration_sec
        self._max_duration_sec = max_duration_sec

    def validate(self, script: EducationalScript, *, raw: RawContent | None = None) -> None:
        if not script.teaching_sections:
            raise ValidationAppError(
                "EducationalScript must include at least one teaching section.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "teaching_sections"},
            )

        section_ids = [s.id for s in script.teaching_sections]
        if len(set(section_ids)) != len(section_ids):
            raise ValidationAppError(
                "teaching_sections.id values must be unique.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "teaching_sections.id"},
            )

        for section in script.teaching_sections:
            if not section.narration.strip() or count_words(section.narration) <= 0:
                raise ValidationAppError(
                    "teaching section narration must be non-empty.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"section_id": section.id},
                )
            if _UNSPEAKABLE.search(section.narration):
                raise ValidationAppError(
                    "teaching section narration contains unspeakable formatting.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"section_id": section.id},
                )

        # Duration only — word totals are reporting metrics, not hard gates.
        metrics = self._calculator.compute(script)
        if metrics.total_duration_sec < self._min_duration_sec:
            raise ValidationAppError(
                f"Estimated duration must be at least {self._min_duration_sec} seconds.",
                code="SCRIPT_VALIDATION_ERROR",
                details={
                    "estimated_duration_sec": metrics.total_duration_sec,
                    "min": self._min_duration_sec,
                },
            )
        if metrics.total_duration_sec > self._max_duration_sec:
            raise ValidationAppError(
                f"Estimated duration must be at most {self._max_duration_sec} seconds.",
                code="SCRIPT_VALIDATION_ERROR",
                details={
                    "estimated_duration_sec": metrics.total_duration_sec,
                    "max": self._max_duration_sec,
                },
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
