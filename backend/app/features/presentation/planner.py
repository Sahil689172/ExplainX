"""Deterministic placeholder PresentationPlanner — no LLM.

Fills the full PresentationPlan schema using heuristics so API consumers and
later phases can integrate against a stable contract before LLM wiring.
"""

from __future__ import annotations

import re
import uuid

from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.presentation.protocols import (
    ConceptExtractor,
    DurationEstimator,
    LanguageDetector,
    ObjectiveBuilder,
    PresentationPlanner,
    SectionOrganizer,
    TitleDetector,
    VisualCandidateDetector,
)
from app.features.presentation.schemas import (
    KeyConcept,
    LearningObjective,
    PresentationPlan,
    TeachingSection,
    VisualCandidate,
)

# ~150 words per minute narration baseline for placeholder estimates.
_WORDS_PER_MINUTE = 150.0
_MIN_DURATION_SEC = 15.0


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class PlaceholderTitleDetector:
    def detect_title(self, raw: RawContent) -> str:
        for section in raw.sections:
            if section.title and section.title.strip():
                return section.title.strip()[:200]
        first_line = raw.text.strip().splitlines()[0].strip() if raw.text.strip() else ""
        if first_line:
            return first_line[:120]
        meta_title = raw.metadata.get("title")
        if isinstance(meta_title, str) and meta_title.strip():
            return meta_title.strip()[:200]
        return "Untitled Presentation"


class PlaceholderLanguageDetector:
    def detect_language(self, raw: RawContent) -> str:
        hint = raw.metadata.get("language_hint")
        if isinstance(hint, str) and len(hint.strip()) >= 2:
            return hint.strip().lower()[:16]
        # Extremely naive heuristic — replaced by a real detector / LLM later.
        sample = raw.text[:500]
        if re.search(r"[\u0900-\u097F]", sample):
            return "hi"
        return "en"


class PlaceholderDurationEstimator:
    def estimate_duration_sec(self, raw: RawContent) -> float:
        words = raw.extraction_stats.word_count or len(re.findall(r"\S+", raw.text))
        minutes = words / _WORDS_PER_MINUTE
        return max(_MIN_DURATION_SEC, round(minutes * 60.0, 1))


class PlaceholderConceptExtractor:
    def extract_concepts(self, raw: RawContent) -> list[KeyConcept]:
        # Placeholder: one concept derived from title-like tokens — not real NLP.
        if raw.sections and raw.sections[0].title:
            label = raw.sections[0].title.strip()
        else:
            words = raw.text.strip().split()
            label = " ".join(words[:4]) if words else "Core topic"
        section_ids = [s.id for s in raw.sections[:1]]
        return [
            KeyConcept(
                id=_new_id("concept"),
                label=label[:200],
                importance=0.5,
                source_section_ids=section_ids,
            )
        ]


class PlaceholderObjectiveBuilder:
    def build_objectives(self, raw: RawContent) -> list[LearningObjective]:
        title_hint = raw.sections[0].title if raw.sections and raw.sections[0].title else "the topic"
        return [
            LearningObjective(
                id=_new_id("objective"),
                text=f"Understand the fundamentals of {title_hint}.",
                bloom_level="understand",
            ),
            LearningObjective(
                id=_new_id("objective"),
                text=f"Explain key ideas related to {title_hint}.",
                bloom_level="understand",
            ),
        ]


class PlaceholderVisualCandidateDetector:
    def detect_visuals(self, raw: RawContent) -> list[VisualCandidate]:
        visuals: list[VisualCandidate] = []
        for section in raw.sections:
            visuals.append(
                VisualCandidate(
                    id=_new_id("visual"),
                    kind="placeholder_diagram",
                    description=f"Placeholder visual for section '{section.title or section.id}'.",
                    section_id=section.id,
                    confidence=0.0,
                )
            )
        if not visuals:
            visuals.append(
                VisualCandidate(
                    id=_new_id("visual"),
                    kind="placeholder_diagram",
                    description="Placeholder overview visual.",
                    section_id=None,
                    confidence=0.0,
                )
            )
        return visuals


class PlaceholderSectionOrganizer:
    def organize_sections(self, raw: RawContent) -> list[TeachingSection]:
        if not raw.sections:
            return [
                TeachingSection(
                    id=_new_id("teach"),
                    order=1,
                    title="Introduction",
                    summary=raw.text[:500],
                    source_section_ids=[],
                    estimated_duration_sec=_MIN_DURATION_SEC,
                )
            ]
        total_words = max(raw.extraction_stats.word_count, 1)
        total_duration = max(
            _MIN_DURATION_SEC,
            round((total_words / _WORDS_PER_MINUTE) * 60.0, 1),
        )
        per_section = round(total_duration / len(raw.sections), 1)
        teaching: list[TeachingSection] = []
        for index, section in enumerate(raw.sections, start=1):
            title = section.title or f"Section {index}"
            teaching.append(
                TeachingSection(
                    id=_new_id("teach"),
                    order=index,
                    title=title[:200],
                    summary=section.text[:500],
                    source_section_ids=[section.id],
                    estimated_duration_sec=per_section,
                )
            )
        return teaching


class PlaceholderPresentationPlanner:
    """Composes placeholder analyzers into a valid PresentationPlan."""

    def __init__(
        self,
        *,
        title_detector: TitleDetector | None = None,
        language_detector: LanguageDetector | None = None,
        duration_estimator: DurationEstimator | None = None,
        concept_extractor: ConceptExtractor | None = None,
        objective_builder: ObjectiveBuilder | None = None,
        visual_detector: VisualCandidateDetector | None = None,
        section_organizer: SectionOrganizer | None = None,
    ) -> None:
        self._title = title_detector or PlaceholderTitleDetector()
        self._language = language_detector or PlaceholderLanguageDetector()
        self._duration = duration_estimator or PlaceholderDurationEstimator()
        self._concepts = concept_extractor or PlaceholderConceptExtractor()
        self._objectives = objective_builder or PlaceholderObjectiveBuilder()
        self._visuals = visual_detector or PlaceholderVisualCandidateDetector()
        self._sections = section_organizer or PlaceholderSectionOrganizer()

    def plan(self, raw: RawContent) -> PresentationPlan:
        title = self._title.detect_title(raw)
        language = self._language.detect_language(raw)
        duration = self._duration.estimate_duration_sec(raw)
        concepts = self._concepts.extract_concepts(raw)
        objectives = self._objectives.build_objectives(raw)
        visuals = self._visuals.detect_visuals(raw)
        teaching = self._sections.organize_sections(raw)

        # Wire cross-references lightly for schema completeness.
        concept_ids = [c.id for c in concepts]
        objective_ids = [o.id for o in objectives]
        for section in teaching:
            section.concept_ids = list(concept_ids)
            section.objective_ids = list(objective_ids)
            section.visual_candidate_ids = [
                v.id for v in visuals if v.section_id in section.source_section_ids
            ]

        return PresentationPlan(
            plan_id=str(uuid.uuid4()),
            project_id=raw.project_id,
            content_id=raw.content_id,
            status="placeholder",
            title=title,
            language=language,
            estimated_duration_sec=duration,
            key_concepts=concepts,
            learning_objectives=objectives,
            visual_candidates=visuals,
            teaching_sections=teaching,
            warnings=[
                "Phase 2.3 placeholder plan — LLM Content Intelligence not wired yet.",
            ],
            metadata={
                "planner": "placeholder_v0",
                "llm": False,
                "source_type": raw.source_type.value,
            },
            created_at=utc_now_iso(),
        )


# Explicit Protocol satisfaction for type checkers / DI.
_: PresentationPlanner = PlaceholderPresentationPlanner()
