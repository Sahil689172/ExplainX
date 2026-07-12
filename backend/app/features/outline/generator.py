"""Deterministic PlaceholderOutlineGenerator — lesson plan only (Phase 3.7)."""

from __future__ import annotations

import uuid

from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.outline.budget import apply_word_budget
from app.features.outline.protocols import OutlineGenerator
from app.features.outline.schemas import (
    OUTLINE_SECTION_MAX,
    OUTLINE_SECTION_MIN,
    TEACHING_OUTLINE_SCHEMA_VERSION,
    TeachingOutline,
    TeachingSection,
)
from app.features.script.processors.common import (
    resolve_concepts,
    resolve_language,
    resolve_title,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# Fixed pedagogical arc (10 sections) — within 8–12.
_SECTION_BLUEPRINT: list[tuple[str, str]] = [
    ("Hook", "Spark curiosity about why this topic matters."),
    ("Big picture", "State the core idea in plain language."),
    ("Key definition", "Define the central concept precisely."),
    ("How it works", "Explain the main process or mechanism step by step."),
    ("Worked example", "Walk through one concrete example."),
    ("Second example", "Reinforce learning with a second short example."),
    ("Common mistakes", "Call out frequent errors and how to avoid them."),
    ("Analogy", "Connect the idea to a familiar everyday analogy."),
    ("Practice tip", "Give a practical tip learners can apply immediately."),
    ("Recap", "Summarize the lesson and the takeaway."),
]


class PlaceholderOutlineGenerator:
    """Build an 8–12 section TeachingOutline without narration or LLM."""

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        total_target_words: int,
    ) -> TeachingOutline:
        title = resolve_title(raw, None)
        language = resolve_language(raw, None)
        concepts = resolve_concepts(raw, None)
        concept_labels = [c.label for c in concepts] or [title]

        # Prefer 10 sections; shrink/grow slightly with source richness.
        section_count = 10
        source_bits = [s.text.strip() for s in raw.sections if s.text.strip()]
        if len(source_bits) >= 8:
            section_count = min(OUTLINE_SECTION_MAX, max(OUTLINE_SECTION_MIN, 8 + len(source_bits) // 4))
        section_count = max(OUTLINE_SECTION_MIN, min(OUTLINE_SECTION_MAX, section_count))

        blueprint = list(_SECTION_BLUEPRINT[: min(section_count, len(_SECTION_BLUEPRINT))])
        while len(blueprint) < section_count:
            i = len(blueprint) + 1
            blueprint.append(
                (f"Extension {i}", f"Deepen understanding of {title} with another teaching beat.")
            )

        sections: list[TeachingSection] = []
        for index, (section_title, objective_seed) in enumerate(blueprint, start=1):
            label = concept_labels[(index - 1) % len(concept_labels)]
            sections.append(
                TeachingSection(
                    id=_new_id("outline"),
                    title=section_title,
                    learning_objective=f"{objective_seed} Focus on {title}.",
                    target_words=1,  # overwritten by apply_word_budget
                    key_concepts=[label, title] if label != title else [title],
                )
            )

        outline = TeachingOutline(
            outline_id=str(uuid.uuid4()),
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=raw.source_type,
            status="placeholder",
            title=title[:200],
            language=language,
            target_duration_sec=target_duration_sec,
            total_target_words=total_target_words,
            sections=sections,
            warnings=[
                "Placeholder outline generator — deterministic lesson plan (no narration)."
            ],
            metadata={
                "generator": "placeholder_outline_v1",
                "llm": False,
                "section_count": len(sections),
            },
            created_at=utc_now_iso(),
            schema_version=TEACHING_OUTLINE_SCHEMA_VERSION,
        )
        return apply_word_budget(outline, total_target_words=total_target_words)


_: OutlineGenerator = PlaceholderOutlineGenerator()
