"""Deterministic PlaceholderSectionGenerator — one section at a time (Phase 3.8)."""

from __future__ import annotations

from app.core.timeutil import utc_now_iso
from app.features.outline.schemas import TeachingOutline, TeachingSection
from app.features.script.metrics import count_words
from app.features.section_generation.protocols import SectionGenerator
from app.features.section_generation.schemas import SectionOutput


def _pad_to_words(text: str, *, target_words: int) -> str:
    words = text.split()
    if len(words) > target_words:
        trimmed = " ".join(words[:target_words]).rstrip(",;:")
        if not trimmed.endswith((".", "!", "?")):
            trimmed += "."
        return trimmed

    fillers = [
        "We keep the explanation clear and practical for every learner.",
        "Notice how each idea connects smoothly to the next teaching beat.",
        "A short example helps the concept stick in long-term memory.",
        "In practice, careful checking turns confusion into confidence.",
        "Finally, we restate the point so the takeaway is unmistakable.",
    ]
    idx = 0
    while len(words) < target_words:
        words.extend(fillers[idx % len(fillers)].split())
        idx += 1
    words = words[:target_words]
    result = " ".join(words)
    if not result.endswith((".", "!", "?")):
        result += "."
    return result


def _summarize(narration: str, *, max_words: int = 28) -> str:
    words = narration.split()
    if len(words) <= max_words:
        summary = narration.strip()
    else:
        summary = " ".join(words[:max_words]).rstrip(",;:") + "…"
    if not summary.endswith((".", "!", "?", "…")):
        summary += "."
    return summary[:1000]


class PlaceholderSectionGenerator:
    """Build narration for one outline section without an LLM."""

    def generate_section(
        self,
        *,
        outline: TeachingOutline,
        section: TeachingSection,
        index: int,
        previous_section_summary: str,
        next_section_title: str | None,
    ) -> SectionOutput:
        concepts = ", ".join(section.key_concepts) or outline.title
        bridge = (
            f"Building on the previous idea — {previous_section_summary} "
            if previous_section_summary.strip()
            else "We begin the lesson here. "
        )
        forward = (
            f" Next we will move toward {next_section_title}."
            if next_section_title
            else " This closes the teaching arc for now."
        )
        seed = (
            f"{bridge}"
            f"In this section, {section.title}, our goal is: {section.learning_objective} "
            f"We focus on {concepts} within {outline.title}. "
            f"The explanation stays speakable, concrete, and easy to follow aloud."
            f"{forward}"
        )
        narration = _pad_to_words(seed, target_words=section.target_words)
        summary = _summarize(narration)

        return SectionOutput(
            outline_section_id=section.id,
            index=index,
            title=section.title,
            narration=narration,
            learning_objective=section.learning_objective,
            key_concepts=list(section.key_concepts),
            target_words=section.target_words,
            summary=summary,
            warnings=[
                "Placeholder section generator — deterministic per-section narration."
            ],
            metadata={
                "generator": "placeholder_section_v1",
                "llm": False,
                "actual_words": count_words(narration),
            },
            created_at=utc_now_iso(),
        )


_: SectionGenerator = PlaceholderSectionGenerator()
