"""Merge SectionOutputs into EducationalScript (Phase 3.8)."""

from __future__ import annotations

import uuid

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
from app.shared.section_output import SectionOutput


class SectionMerger:
    """Assemble independently generated sections into one EducationalScript."""

    def merge(
        self,
        outline: TeachingOutline,
        outputs: list[SectionOutput],
        *,
        warnings: list[str] | None = None,
        metadata: dict | None = None,
    ) -> EducationalScript:
        if len(outputs) != len(outline.sections):
            raise ValueError(
                f"Expected {len(outline.sections)} section outputs, got {len(outputs)}"
            )

        ordered = sorted(outputs, key=lambda item: item.index)
        teaching_sections: list[TeachingSection] = []
        for output in ordered:
            teaching_sections.append(
                TeachingSection(
                    id=output.outline_section_id,
                    title=output.title,
                    narration=output.narration.strip(),
                    estimated_duration_sec=0.0,
                    estimated_words=0,
                    concept_tags=list(output.key_concepts) or list(
                        next(
                            (
                                s.key_concepts
                                for s in outline.sections
                                if s.id == output.outline_section_id
                            ),
                            [],
                        )
                    ),
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
            concepts = [ScriptConcept(id=f"concept-{uuid.uuid4().hex[:8]}", label=outline.title)]

        objectives = [
            section.learning_objective.strip()
            for section in outline.sections
            if section.learning_objective.strip()
        ]
        summary = (
            f"A structured {outline.target_duration_sec}-second educational explanation "
            f"of {outline.title}, taught across {len(ordered)} sections."
        )

        out_warnings = list(warnings or [])
        out_warnings.append(
            "Assembled by SectionMerger from independently generated section narrations."
        )
        for output in ordered:
            out_warnings.extend(output.warnings)

        script = EducationalScript(
            script_id=str(uuid.uuid4()),
            project_id=outline.project_id,
            content_id=outline.content_id,
            source_type=outline.source_type,
            status="draft" if any(o.metadata.get("llm") for o in ordered) else "placeholder",
            title=outline.title[:200],
            language=outline.language,
            target_duration_sec=outline.target_duration_sec or V1_TARGET_DURATION_SEC,
            estimated_duration_sec=0.0,
            estimated_word_count=0,
            estimated_scene_count=0,
            summary=summary[:2000],
            key_concepts=concepts,
            learning_objectives=objectives,
            teaching_sections=teaching_sections,
            warnings=out_warnings,
            metadata={
                "generator": "section_generation_v1",
                "teaching_outline_id": outline.outline_id,
                "outline_section_count": len(outline.sections),
                "outline_total_target_words": outline.total_target_words,
                "section_generation": True,
                **(metadata or {}),
            },
            created_at=utc_now_iso(),
            schema_version=EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
        )
        return enrich_script_with_metrics(script)
