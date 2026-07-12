"""Word-budget helpers for TeachingOutline (140 WPM)."""

from __future__ import annotations

from app.features.script.durations import V1_TARGET_DURATION_SEC, V1_WPM
from app.features.outline.schemas import TeachingOutline, TeachingSection

# Accept tiny integer rounding drift after distribution (normally exact).
WORD_BUDGET_TOLERANCE = 2


def compute_total_word_budget(target_duration_sec: int | None = None) -> int:
    """Total spoken-word budget from duration at 140 words/minute."""
    duration = target_duration_sec or V1_TARGET_DURATION_SEC
    if duration < 1:
        raise ValueError("target_duration_sec must be >= 1")
    return int(round((V1_WPM / 60.0) * duration))


def distribute_word_budget(total_words: int, section_count: int) -> list[int]:
    """Split ``total_words`` across ``section_count`` sections (remainder first)."""
    if section_count < 1:
        raise ValueError("section_count must be >= 1")
    if total_words < section_count:
        raise ValueError("total_words must be >= section_count")
    base = total_words // section_count
    remainder = total_words % section_count
    return [base + (1 if i < remainder else 0) for i in range(section_count)]


def apply_word_budget(
    outline: TeachingOutline,
    *,
    total_target_words: int | None = None,
) -> TeachingOutline:
    """Overwrite section ``target_words`` so they sum exactly to the budget."""
    total = total_target_words if total_target_words is not None else outline.total_target_words
    allocations = distribute_word_budget(total, len(outline.sections))
    sections: list[TeachingSection] = []
    for section, words in zip(outline.sections, allocations, strict=True):
        sections.append(section.model_copy(update={"target_words": words}))
    return outline.model_copy(
        update={
            "total_target_words": total,
            "sections": sections,
        }
    )
