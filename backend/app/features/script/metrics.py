"""Deterministic script metrics — never trust LLM numerical metadata."""

from __future__ import annotations

import re

from app.features.script.durations import (
    V1_WPM,
    duration_from_words,
    estimate_scene_count,
)
from app.features.script.schemas import EducationalScript, ScriptMetrics, TeachingSection

_WORD_RE = re.compile(r"\S+")


def count_words(text: str) -> int:
    """Count whitespace-delimited tokens in narration text."""
    return len(_WORD_RE.findall(text or ""))


def estimate_reading_level(*, total_words: int, section_count: int) -> str:
    """Lightweight heuristic reading-level label (not a full readability suite)."""
    if total_words <= 0:
        return "unknown"
    avg = total_words / max(section_count, 1)
    if avg < 35:
        return "beginner"
    if avg < 70:
        return "intermediate"
    return "advanced"


class ScriptMetricsCalculator:
    """Count words and derive all duration / scene metadata at 140 WPM.

    Generators must produce narration (and titles/concepts) only.
    This calculator owns every numerical estimate on EducationalScript.
    """

    wpm: float = V1_WPM

    def words_for_narration(self, narration: str) -> int:
        return count_words(narration)

    def duration_for_words(self, word_count: int) -> float:
        return duration_from_words(word_count, wpm=self.wpm)

    def duration_for_narration(self, narration: str) -> float:
        return self.duration_for_words(self.words_for_narration(narration))

    def metrics_for_section(self, section: TeachingSection) -> TeachingSection:
        """Return a copy with estimated_words / estimated_duration_sec from narration."""
        words = self.words_for_narration(section.narration)
        return section.model_copy(
            update={
                "estimated_words": words,
                "estimated_duration_sec": self.duration_for_words(words),
            }
        )

    def apply(self, script: EducationalScript) -> EducationalScript:
        """Overwrite all numerical metadata from teaching-section narration."""
        sections = [self.metrics_for_section(section) for section in script.teaching_sections]
        updated = script.model_copy(update={"teaching_sections": sections})
        metrics = self.compute(updated)
        return updated.model_copy(
            update={
                "estimated_word_count": metrics.total_words,
                "estimated_duration_sec": metrics.total_duration_sec,
                "estimated_scene_count": metrics.estimated_scene_count,
            }
        )

    def compute(self, script: EducationalScript) -> ScriptMetrics:
        """Derive ScriptMetrics from narration (ignores stored estimated_* fields)."""
        section_words = [
            self.words_for_narration(section.narration) for section in script.teaching_sections
        ]
        total_words = sum(section_words) or self.words_for_narration(script.full_text)
        total_duration = self.duration_for_words(total_words)
        scene_count = estimate_scene_count(total_duration)
        section_count = max(len(script.teaching_sections), 1)
        average = round(total_words / section_count, 1)

        return ScriptMetrics(
            total_words=total_words,
            total_duration_sec=total_duration,
            estimated_duration_sec=total_duration,
            estimated_scene_count=scene_count,
            average_words_per_section=average,
            reading_level=estimate_reading_level(
                total_words=total_words,
                section_count=section_count,
            ),
            language=script.language,
        )


def enrich_script_with_metrics(script: EducationalScript) -> EducationalScript:
    """Fill all estimated_* fields from narration via ScriptMetricsCalculator."""
    return ScriptMetricsCalculator().apply(script)
