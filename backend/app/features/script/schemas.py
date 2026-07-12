"""EducationalScript artifact — Phase 3 Content Intelligence output."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import SourceType

EDUCATIONAL_SCRIPT_SCHEMA_VERSION = "1.0"

ScriptStatus = Literal["placeholder", "draft", "ready"]


class ScriptBeat(BaseModel):
    """TTS-friendly narration unit (maps to constitution NarrationScript beats)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    order: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=2000)
    section_id: str
    scene_hint: str | None = Field(default=None, max_length=64)
    approx_sec: float = Field(ge=0.0)
    concept_ids: list[str] = Field(default_factory=list)


class ScriptSection(BaseModel):
    """Educational narration section with ordered beats."""

    model_config = ConfigDict(extra="forbid")

    id: str
    order: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    narration_text: str = Field(min_length=1, max_length=50_000)
    estimated_duration_sec: float = Field(ge=0.0)
    beat_ids: list[str] = Field(default_factory=list)
    concept_ids: list[str] = Field(default_factory=list)
    source_section_ids: list[str] = Field(default_factory=list)


class ScriptConcept(BaseModel):
    """Concept preserved from source / plan for downstream scene planning."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str = Field(min_length=1, max_length=200)


class EducationalScript(BaseModel):
    """Common educational narration script for every input type.

    Produced from topic / PDF / custom script via ContentIntelligenceService.
    ``PlaceholderContentGenerator`` may later be replaced by
    ``OllamaContentGenerator`` without changing this schema.
    """

    model_config = ConfigDict(extra="forbid")

    script_id: str
    project_id: str
    content_id: str
    source_type: SourceType
    status: ScriptStatus = "placeholder"
    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=16)
    full_text: str = Field(min_length=1)
    sections: list[ScriptSection] = Field(min_length=1)
    beats: list[ScriptBeat] = Field(min_length=1)
    key_concepts: list[ScriptConcept] = Field(default_factory=list)
    estimated_duration_sec: float = Field(ge=0.0)
    target_duration_sec: int | None = Field(default=None, ge=1)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    schema_version: str = EDUCATIONAL_SCRIPT_SCHEMA_VERSION

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if len(cleaned) < 2:
            raise ValueError("language must be at least 2 characters")
        return cleaned


class GenerateScriptRequest(BaseModel):
    """Optional body for POST /projects/{id}/script (Phase 3)."""

    model_config = ConfigDict(extra="forbid")

    target_duration: str | None = Field(
        default=None,
        description="One of: 30s, 60s, 90s, 3min, 5min",
    )
    target_duration_sec: int | None = Field(
        default=None,
        description="Explicit seconds; must be 30, 60, 90, 180, or 300",
    )
