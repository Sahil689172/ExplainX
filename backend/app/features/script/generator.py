"""Deterministic PlaceholderScriptGenerator — no LLM / Ollama."""

from __future__ import annotations

import re
import uuid

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent, RawContentSection
from app.features.presentation.schemas import PresentationPlan
from app.features.script.protocols import ScriptGenerator
from app.features.script.schemas import (
    EducationalScript,
    ScriptBeat,
    ScriptConcept,
    ScriptSection,
)

_WORDS_PER_MINUTE = 150.0
_MIN_BEAT_SEC = 2.0
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _approx_sec(text: str) -> float:
    words = _word_count(text)
    return max(_MIN_BEAT_SEC, round((words / _WORDS_PER_MINUTE) * 60.0, 1))


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


class PlaceholderScriptGenerator:
    """Normalize RawContent into EducationalScript with TTS-friendly beats.

    Source-specific handling:
    - ``topic``: wrap in a short teaching narration template
    - ``script``: preserve author text as narration (light normalization)
    - ``pdf`` (and other): speak section text with light connective phrasing
    """

    def generate(
        self,
        raw: RawContent,
        *,
        plan: PresentationPlan | None = None,
    ) -> EducationalScript:
        title = self._title(raw, plan)
        language = self._language(raw, plan)
        concepts = self._concepts(raw, plan)

        sections: list[ScriptSection] = []
        beats: list[ScriptBeat] = []
        beat_order = 1

        source_sections = raw.sections or [
            RawContentSection(id="section-1", text=raw.text, order=1, title=title)
        ]

        for index, source in enumerate(source_sections, start=1):
            narration = self._narration_for_section(raw.source_type, source, title=title, index=index)
            section_id = _new_id("script-section")
            section_beats: list[ScriptBeat] = []
            sentences = _split_sentences(narration)
            for sentence in sentences:
                hint = "intro" if index == 1 and beat_order == 1 else f"section_{index}"
                beat = ScriptBeat(
                    id=_new_id("nar"),
                    order=beat_order,
                    text=sentence,
                    section_id=section_id,
                    scene_hint=hint,
                    approx_sec=_approx_sec(sentence),
                    concept_ids=[c.id for c in concepts],
                )
                section_beats.append(beat)
                beats.append(beat)
                beat_order += 1

            section_text = " ".join(b.text for b in section_beats)
            sections.append(
                ScriptSection(
                    id=section_id,
                    order=index,
                    title=(source.title or f"Section {index}")[:200],
                    narration_text=section_text,
                    estimated_duration_sec=round(sum(b.approx_sec for b in section_beats), 1),
                    beat_ids=[b.id for b in section_beats],
                    concept_ids=[c.id for c in concepts],
                    source_section_ids=[source.id],
                )
            )

        full_text = "\n\n".join(s.narration_text for s in sections)
        total_duration = round(sum(s.estimated_duration_sec for s in sections), 1)

        return EducationalScript(
            script_id=str(uuid.uuid4()),
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=raw.source_type,
            status="placeholder",
            title=title,
            language=language,
            full_text=full_text,
            sections=sections,
            beats=beats,
            key_concepts=concepts,
            estimated_duration_sec=total_duration,
            warnings=[
                "Placeholder script generator — Ollama/LLM ScriptGenerator not wired yet.",
            ],
            metadata={
                "generator": "placeholder_v0",
                "llm": False,
                "used_presentation_plan": plan is not None,
                "plan_id": plan.plan_id if plan else None,
            },
            created_at=utc_now_iso(),
        )

    def _title(self, raw: RawContent, plan: PresentationPlan | None) -> str:
        if plan and plan.title.strip():
            return plan.title.strip()[:200]
        for section in raw.sections:
            if section.title and section.title.strip():
                return section.title.strip()[:200]
        first = raw.text.strip().splitlines()[0].strip() if raw.text.strip() else ""
        return (first[:120] if first else "Educational Script")

    def _language(self, raw: RawContent, plan: PresentationPlan | None) -> str:
        if plan and plan.language:
            return plan.language
        hint = raw.metadata.get("language_hint")
        if isinstance(hint, str) and len(hint.strip()) >= 2:
            return hint.strip().lower()[:16]
        return "en"

    def _concepts(self, raw: RawContent, plan: PresentationPlan | None) -> list[ScriptConcept]:
        if plan and plan.key_concepts:
            return [
                ScriptConcept(id=c.id, label=c.label) for c in plan.key_concepts
            ]
        label = (
            raw.sections[0].title.strip()
            if raw.sections and raw.sections[0].title
            else " ".join(raw.text.strip().split()[:4]) or "Core topic"
        )
        return [ScriptConcept(id=_new_id("concept"), label=label[:200])]

    def _narration_for_section(
        self,
        source_type: SourceType,
        section: RawContentSection,
        *,
        title: str,
        index: int,
    ) -> str:
        body = " ".join(section.text.split()).strip()
        if not body:
            body = title

        if source_type == SourceType.TOPIC:
            if index == 1:
                return (
                    f"Today we will learn about {title}. "
                    f"{body} "
                    f"Let's explore this idea step by step."
                )
            return f"Next, {body}"

        if source_type == SourceType.SCRIPT:
            # Preserve custom script wording; only normalize whitespace.
            return body

        # PDF and other document extracts — light spoken framing.
        if index == 1:
            return f"Let's begin. {body}"
        return f"Moving on. {body}"


_: ScriptGenerator = PlaceholderScriptGenerator()
