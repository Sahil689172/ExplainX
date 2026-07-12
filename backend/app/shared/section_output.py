"""Shared SectionOutput model — used by section generation and quality repair."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SECTION_OUTPUT_SCHEMA_VERSION = "1.0"


class SectionOutput(BaseModel):
    """Narration produced for a single TeachingOutline section.

    Numerical estimates are not stored here — ``ScriptMetricsCalculator``
    derives them after merge into EducationalScript.
    """

    model_config = ConfigDict(extra="forbid")

    outline_section_id: str = Field(min_length=1, max_length=64)
    index: int = Field(ge=1, le=99)
    title: str = Field(min_length=1, max_length=200)
    narration: str = Field(min_length=1, max_length=50_000)
    learning_objective: str = Field(min_length=1, max_length=500)
    key_concepts: list[str] = Field(default_factory=list)
    target_words: int = Field(ge=1)
    summary: str = Field(
        min_length=1,
        max_length=1000,
        description="Short summary used as context for the next section.",
    )
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    schema_version: str = SECTION_OUTPUT_SCHEMA_VERSION
