"""Compute ScriptMetrics for a standardized EducationalScript."""

from __future__ import annotations

import re

from app.features.script.durations import (
    V1_WPM,
    duration_from_words,
    estimate_scene_count,
)
from app.features.script.schemas import EducationalScript, ScriptMetrics

_WORD_RE = re.compile(r"\S+")


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def estimate_reading_level(*, total_words: int, section_count: int) -> str:
    """Lightweight heuristic reading-level label (not a full readability suite)."""
    if total_words <= 0:
        return "unknown"
    avg = total_words / max(section_count, 1)
    # Short sections + moderate total → beginner/intermediate educational voice.
    if avg < 35:
        return "beginner"
    if avg < 70:
        return "intermediate"
    return "advanced"


class ScriptMetricsCalculator:
    """Derive ScriptMetrics from an EducationalScript."""

    def compute(self, script: EducationalScript) -> ScriptMetrics:
        section_words = [count_words(s.narration) for s in script.teaching_sections]
        total_words = sum(section_words) or count_words(script.full_text)
        duration = duration_from_words(total_words, wpm=V1_WPM)
        scene_count = estimate_scene_count(duration)
        section_count = max(len(script.teaching_sections), 1)
        average = round(total_words / section_count, 1)

        return ScriptMetrics(
            total_words=total_words,
            estimated_duration_sec=duration,
            estimated_scene_count=scene_count,
            average_words_per_section=average,
            reading_level=estimate_reading_level(
                total_words=total_words,
                section_count=section_count,
            ),
            language=script.language,
        )


def enrich_script_with_metrics(script: EducationalScript) -> EducationalScript:
    """Fill estimated_* fields from teaching_sections when missing or stale."""
    metrics = ScriptMetricsCalculator().compute(script)
    return script.model_copy(
        update={
            "estimated_word_count": metrics.total_words,
            "estimated_duration_sec": metrics.estimated_duration_sec,
            "estimated_scene_count": metrics.estimated_scene_count,
        }
    )
