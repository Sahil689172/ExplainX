"""Deterministic PlaceholderContentGenerator — no LLM / Ollama."""

from __future__ import annotations

import re
import uuid

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent, RawContentSection
from app.features.presentation.schemas import PresentationPlan
from app.features.script.durations import WORDS_PER_MINUTE, label_for_seconds, word_budget
from app.features.script.protocols import ContentGenerator
from app.features.script.schemas import (
    EducationalScript,
    ScriptBeat,
    ScriptConcept,
    ScriptSection,
)

_MIN_BEAT_SEC = 2.0
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _approx_sec(text: str) -> float:
    words = _word_count(text)
    return max(_MIN_BEAT_SEC, round((words / WORDS_PER_MINUTE) * 60.0, 1))


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _trim_to_budget(text: str, budget: int) -> str:
    words = text.split()
    if len(words) <= budget:
        return " ".join(words)
    trimmed = " ".join(words[:budget]).rstrip(",;:")
    if not trimmed.endswith((".", "!", "?")):
        trimmed += "."
    return trimmed


class PlaceholderContentGenerator:
    """Build TTS-friendly EducationalScript beats sized to a target duration.

    Later: inject ``OllamaContentGenerator`` with the same ``generate`` signature.
    """

    def generate(
        self,
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        title: str,
        language: str,
        sections: list[RawContentSection],
        concepts: list[ScriptConcept],
        target_duration_sec: int,
        warnings: list[str] | None = None,
        metadata: dict | None = None,
    ) -> EducationalScript:
        budget = word_budget(target_duration_sec)
        source_sections = sections or [
            RawContentSection(id="section-1", text=title, order=1, title=title)
        ]

        # Allocate words across sections (prefer earlier sections slightly).
        weights = [max(1, len(s.text.split()) or 1) for s in source_sections]
        weight_sum = sum(weights) or 1
        section_budgets = [
            max(12, int(round(budget * (w / weight_sum)))) for w in weights
        ]
        # Fix rounding drift on the last section.
        drift = budget - sum(section_budgets)
        section_budgets[-1] = max(12, section_budgets[-1] + drift)

        out_sections: list[ScriptSection] = []
        beats: list[ScriptBeat] = []
        beat_order = 1
        out_warnings = list(warnings or [])
        out_warnings.append(
            "Placeholder content generator — deterministic fallback (no LLM)."
        )

        for index, (source, sec_budget) in enumerate(
            zip(source_sections, section_budgets, strict=True),
            start=1,
        ):
            narration = _trim_to_budget(" ".join(source.text.split()), sec_budget)
            if not narration:
                narration = _trim_to_budget(title, sec_budget)

            section_id = _new_id("script-section")
            section_beats: list[ScriptBeat] = []
            for sentence in _split_sentences(narration):
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
            out_sections.append(
                ScriptSection(
                    id=section_id,
                    order=index,
                    title=(source.title or f"Section {index}")[:200],
                    narration_text=section_text,
                    estimated_duration_sec=round(
                        sum(b.approx_sec for b in section_beats), 1
                    ),
                    beat_ids=[b.id for b in section_beats],
                    concept_ids=[c.id for c in concepts],
                    source_section_ids=[source.id],
                )
            )

        full_text = "\n\n".join(s.narration_text for s in out_sections)
        total_duration = round(sum(s.estimated_duration_sec for s in out_sections), 1)

        meta = {
            "generator": "placeholder_content_v1",
            "llm": False,
            "target_duration": label_for_seconds(target_duration_sec),
            "target_duration_sec": target_duration_sec,
            "word_budget": budget,
            **(metadata or {}),
        }

        return EducationalScript(
            script_id=str(uuid.uuid4()),
            project_id=project_id,
            content_id=content_id,
            source_type=source_type,
            status="placeholder",
            title=title[:200],
            language=language,
            full_text=full_text,
            sections=out_sections,
            beats=beats,
            key_concepts=concepts,
            estimated_duration_sec=total_duration,
            target_duration_sec=target_duration_sec,
            warnings=out_warnings,
            metadata=meta,
            created_at=utc_now_iso(),
        )


_: ContentGenerator = PlaceholderContentGenerator()


class PlaceholderScriptGenerator:
    """Legacy facade used by older unit tests — routes through Phase 3 processors."""

    def __init__(self, generator: ContentGenerator | None = None) -> None:
        # Local imports avoid circular dependency at module import time.
        from app.features.script.processors.pdf_processor import PDFContentProcessor
        from app.features.script.processors.script_processor import ScriptContentProcessor
        from app.features.script.processors.topic_processor import TopicContentProcessor

        self._generator = generator or PlaceholderContentGenerator()
        self._processors = {
            SourceType.TOPIC: TopicContentProcessor(self._generator),
            SourceType.SCRIPT: ScriptContentProcessor(self._generator),
            SourceType.PDF: PDFContentProcessor(self._generator),
        }

    def generate(
        self,
        raw: RawContent,
        *,
        plan: PresentationPlan | None = None,
        target_duration_sec: int = 60,
    ) -> EducationalScript:
        processor = self._processors.get(raw.source_type)
        if processor is None:
            from app.features.script.processors.topic_processor import TopicContentProcessor

            processor = TopicContentProcessor(self._generator)
        return processor.process(
            raw,
            target_duration_sec=target_duration_sec,
            plan=plan,
            pdf_path=None,
        )
