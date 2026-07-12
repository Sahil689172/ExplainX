"""EducationalScript artifact — Phase 3.6 standardized V1 narration format."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import SourceType
from app.features.script.durations import V1_TARGET_DURATION_SEC

EDUCATIONAL_SCRIPT_SCHEMA_VERSION = "1.1"

ScriptStatus = Literal["placeholder", "draft", "ready"]


class ScriptConcept(BaseModel):
    """Concept preserved for downstream scene planning."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str = Field(min_length=1, max_length=200)


class TeachingSection(BaseModel):
    """One teachable narration block inside the 2–3 minute explainer."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=1, max_length=200)
    narration: str = Field(min_length=1, max_length=50_000)
    estimated_duration_sec: float = Field(ge=0.0)
    estimated_words: int = Field(ge=0)
    concept_tags: list[str] = Field(default_factory=list)


class EducationalScript(BaseModel):
    """V1 high-quality educational narration for a 2–3 minute explainer.

    Target band: 120–180 seconds, ~320–420 words, ~18–25 estimated scenes.

    Numerical fields (``estimated_*``) are always filled by
    ``ScriptMetricsCalculator`` from narration at 140 WPM — never guessed
    by an LLM.
    """

    model_config = ConfigDict(extra="forbid")

    script_id: str
    project_id: str
    content_id: str
    source_type: SourceType
    status: ScriptStatus = "placeholder"

    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=16)
    target_duration_sec: int = Field(default=V1_TARGET_DURATION_SEC, ge=1)
    estimated_duration_sec: float = Field(ge=0.0)
    estimated_word_count: int = Field(ge=0)
    estimated_scene_count: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=2000)
    key_concepts: list[ScriptConcept] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    teaching_sections: list[TeachingSection] = Field(min_length=1)

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

    @property
    def full_text(self) -> str:
        """Concatenated narration for TTS / legacy consumers."""
        return "\n\n".join(section.narration for section in self.teaching_sections)


class ScriptMetrics(BaseModel):
    """Derived metrics for a standardized EducationalScript.

    All values are calculated from narration at 140 WPM — never from the LLM.
    """

    model_config = ConfigDict(extra="forbid")

    total_words: int = Field(ge=0)
    total_duration_sec: float = Field(
        ge=0.0,
        description="Total speaking duration in seconds (alias of estimated_duration_sec).",
    )
    estimated_duration_sec: float = Field(ge=0.0)
    estimated_scene_count: int = Field(ge=0)
    average_words_per_section: float = Field(ge=0.0)
    reading_level: str = Field(min_length=1, max_length=64)
    language: str = Field(min_length=2, max_length=16)

    @model_validator(mode="before")
    @classmethod
    def _backfill_total_duration(cls, data: Any) -> Any:
        if isinstance(data, dict) and "total_duration_sec" not in data:
            if "estimated_duration_sec" in data:
                data = {**data, "total_duration_sec": data["estimated_duration_sec"]}
        return data


class GenerateScriptRequest(BaseModel):
    """Optional body for POST /projects/{id}/script (API-compatible; V1 ignores presets)."""

    model_config = ConfigDict(extra="forbid")

    target_duration: str | None = Field(
        default=None,
        description="Ignored in V1 — ExplainX always targets a 2–3 minute explainer.",
    )
    target_duration_sec: int | None = Field(
        default=None,
        description="Ignored in V1 — canonical target is 150 seconds (120–180 accepted).",
    )


# Backward-compatible aliases removed from the public schema surface.
# Older beat/section models are intentionally retired in Phase 3.6.
