"""TeachingOutline schemas — lesson plan only (no narration). Phase 3.7."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import SourceType
from app.features.script.durations import V1_TARGET_DURATION_SEC

TEACHING_OUTLINE_SCHEMA_VERSION = "1.0"

OutlineStatus = Literal["placeholder", "draft", "ready"]

OUTLINE_SECTION_MIN = 8
OUTLINE_SECTION_MAX = 12


class TeachingSection(BaseModel):
    """One logical teaching unit in a lesson plan (not spoken narration).

    Distinct from ``script.schemas.TeachingSection``, which holds narration text.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    learning_objective: str = Field(min_length=1, max_length=500)
    target_words: int = Field(ge=1)
    key_concepts: list[str] = Field(default_factory=list, min_length=1)


class TeachingOutline(BaseModel):
    """Intermediate lesson plan: RawContent → TeachingOutline → EducationalScript."""

    model_config = ConfigDict(extra="forbid")

    outline_id: str
    project_id: str
    content_id: str
    source_type: SourceType
    status: OutlineStatus = "placeholder"

    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=16)
    target_duration_sec: int = Field(default=V1_TARGET_DURATION_SEC, ge=1)
    total_target_words: int = Field(ge=1)
    sections: list[TeachingSection] = Field(
        min_length=OUTLINE_SECTION_MIN,
        max_length=OUTLINE_SECTION_MAX,
    )

    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    schema_version: str = TEACHING_OUTLINE_SCHEMA_VERSION

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if len(cleaned) < 2:
            raise ValueError("language must be at least 2 characters")
        return cleaned

    @property
    def allocated_words(self) -> int:
        return sum(section.target_words for section in self.sections)
