"""Protocols (interfaces) for Content Intelligence — LLM adapters plug in later."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.input.schemas import RawContent
from app.features.presentation.schemas import (
    KeyConcept,
    LearningObjective,
    PresentationPlan,
    TeachingSection,
    VisualCandidate,
)


@runtime_checkable
class TitleDetector(Protocol):
    def detect_title(self, raw: RawContent) -> str: ...


@runtime_checkable
class LanguageDetector(Protocol):
    def detect_language(self, raw: RawContent) -> str: ...


@runtime_checkable
class DurationEstimator(Protocol):
    def estimate_duration_sec(self, raw: RawContent) -> float: ...


@runtime_checkable
class ConceptExtractor(Protocol):
    def extract_concepts(self, raw: RawContent) -> list[KeyConcept]: ...


@runtime_checkable
class ObjectiveBuilder(Protocol):
    def build_objectives(self, raw: RawContent) -> list[LearningObjective]: ...


@runtime_checkable
class VisualCandidateDetector(Protocol):
    def detect_visuals(self, raw: RawContent) -> list[VisualCandidate]: ...


@runtime_checkable
class SectionOrganizer(Protocol):
    def organize_sections(self, raw: RawContent) -> list[TeachingSection]: ...


@runtime_checkable
class PresentationPlanner(Protocol):
    """Compose analyzers into a PresentationPlan (placeholder or LLM-backed)."""

    def plan(self, raw: RawContent) -> PresentationPlan: ...
