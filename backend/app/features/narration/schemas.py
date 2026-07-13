"""Narration artifact — continuous spoken lesson text (no scenes)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SourceType

NARRATION_SCHEMA_VERSION = "1.0"

NarrationStatus = Literal["placeholder", "draft", "ready"]


class NarrationDocument(BaseModel):
    """Continuous educational narration produced by the LLM (or author script)."""

    model_config = ConfigDict(extra="forbid")

    narration_id: str
    project_id: str
    content_id: str
    source_type: SourceType
    status: NarrationStatus = "draft"

    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=16)
    text: str = Field(min_length=1, max_length=200_000)
    target_duration_sec: int = Field(ge=1)

    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    schema_version: str = NARRATION_SCHEMA_VERSION
