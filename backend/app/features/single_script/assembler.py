"""Assemble TeachingOutline + narrated sections into EducationalScript."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.timeutil import utc_now_iso
from app.features.outline.schemas import TeachingOutline
from app.features.script.durations import V1_TARGET_DURATION_SEC
from app.features.script.metrics import enrich_script_with_metrics
from app.features.script.schemas import (
    EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
    EducationalScript,
    ScriptConcept,
    TeachingSection,
)


def assemble_educational_script(
    outline: TeachingOutline,
    *,
    narrations: dict[str, str],
    title: str | None = None,
    warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> EducationalScript:
    """Build EducationalScript from outline order + narration map (by section id)."""
    missing = [s.id for s in outline.sections if s.id not in narrations]
    if missing:
        raise ValueError(f"Missing narrations for outline sections: {missing}")

    teaching_sections: list[TeachingSection] = []
    for section in outline.sections:
        narration = narrations[section.id].strip()
        if not narration:
            raise ValueError(f"Empty narration for section {section.id}")
        teaching_sections.append(
            TeachingSection(
                id=section.id,
                title=section.title,
                narration=narration,
                estimated_duration_sec=0.0,
                estimated_words=0,
                concept_tags=list(section.key_concepts),
            )
        )

    concepts: list[ScriptConcept] = []
    seen: set[str] = set()
    for section in outline.sections:
        for label in section.key_concepts:
            key = label.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            concepts.append(
                ScriptConcept(id=f"concept-{uuid.uuid4().hex[:8]}", label=label[:200])
            )
    if not concepts:
        concepts = [
            ScriptConcept(id=f"concept-{uuid.uuid4().hex[:8]}", label=outline.title)
        ]

    objectives = [
        section.learning_objective.strip()
        for section in outline.sections
        if section.learning_objective.strip()
    ]
    resolved_title = (title or outline.title).strip()[:200] or outline.title
    summary = (
        f"A structured {outline.target_duration_sec}-second educational explanation "
        f"of {resolved_title}, taught across {len(teaching_sections)} sections."
    )

    script = EducationalScript(
        script_id=str(uuid.uuid4()),
        project_id=outline.project_id,
        content_id=outline.content_id,
        source_type=outline.source_type,
        status="draft" if (metadata or {}).get("llm") else "placeholder",
        title=resolved_title,
        language=outline.language,
        target_duration_sec=outline.target_duration_sec or V1_TARGET_DURATION_SEC,
        estimated_duration_sec=0.0,
        estimated_word_count=0,
        estimated_scene_count=0,
        summary=summary[:2000],
        key_concepts=concepts,
        learning_objectives=objectives,
        teaching_sections=teaching_sections,
        warnings=list(warnings or []),
        metadata={
            "generator": "single_script_v1",
            "teaching_outline_id": outline.outline_id,
            "outline_section_count": len(outline.sections),
            "outline_total_target_words": outline.total_target_words,
            "single_script_generation": True,
            "section_generation": False,
            **(metadata or {}),
        },
        created_at=utc_now_iso(),
        schema_version=EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
    )
    return enrich_script_with_metrics(script)
