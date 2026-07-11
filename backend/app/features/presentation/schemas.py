"""PresentationPlan artifact — Phase 2.3 Content Intelligence output."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PRESENTATION_PLAN_SCHEMA_VERSION = "1.0"

PlanStatus = Literal["placeholder", "draft", "ready"]


class KeyConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str = Field(min_length=1, max_length=200)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    source_section_ids: list[str] = Field(default_factory=list)


class LearningObjective(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1, max_length=500)
    bloom_level: str | None = Field(default=None, max_length=64)


class VisualCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str = Field(min_length=1, max_length=64)  # diagram | metaphor | formula | ...
    description: str = Field(min_length=1, max_length=500)
    section_id: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class TeachingSection(BaseModel):
    """Logically organized teaching unit derived from RawContent sections."""

    model_config = ConfigDict(extra="forbid")

    id: str
    order: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=2000)
    source_section_ids: list[str] = Field(default_factory=list)
    estimated_duration_sec: float = Field(default=0.0, ge=0.0)
    concept_ids: list[str] = Field(default_factory=list)
    objective_ids: list[str] = Field(default_factory=list)
    visual_candidate_ids: list[str] = Field(default_factory=list)


class PresentationPlan(BaseModel):
    """Educational plan produced from RawContent (LLM-backed later).

    Phase 2.3 emits ``status=placeholder`` with the full schema so
    downstream phases can integrate against a stable contract.
    """

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    project_id: str
    content_id: str
    status: PlanStatus = "placeholder"
    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=16)
    estimated_duration_sec: float = Field(ge=0.0)
    key_concepts: list[KeyConcept] = Field(default_factory=list)
    learning_objectives: list[LearningObjective] = Field(default_factory=list)
    visual_candidates: list[VisualCandidate] = Field(default_factory=list)
    teaching_sections: list[TeachingSection] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    schema_version: str = PRESENTATION_PLAN_SCHEMA_VERSION

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if len(cleaned) < 2:
            raise ValueError("language must be at least 2 characters")
        return cleaned
