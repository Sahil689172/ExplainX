"""Input feature schemas — HTTP models + RawContent artifact."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import SourceType

RAW_CONTENT_SCHEMA_VERSION = "1.0"


class RawContentSection(BaseModel):
    """Ordered text unit (topic block, PDF page, or script paragraph)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    order: int = Field(ge=1)
    title: str | None = None


class ExtractionStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    char_count: int = Field(ge=0)
    word_count: int = Field(ge=0, default=0)
    page_count: int = Field(ge=0, default=0)
    section_count: int = Field(ge=0, default=0)


class RawContent(BaseModel):
    """Canonical ingestion result for every supported input type.

    Downstream phases (cleaning, knowledge, …) consume this schema only —
    never the original upload bytes or processor-specific structures.
    """

    model_config = ConfigDict(extra="forbid")

    content_id: str
    project_id: str
    source_type: SourceType
    text: str
    sections: list[RawContentSection]
    warnings: list[str] = Field(default_factory=list)
    extraction_stats: ExtractionStats
    source_path: str | None = None
    source_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    schema_version: str = RAW_CONTENT_SCHEMA_VERSION


class TopicSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=3, max_length=500)
    replace: bool = False
    language_hint: str | None = Field(default=None, max_length=16)

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("topic must be at least 3 characters")
        return cleaned


class ScriptSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: str = Field(min_length=10, max_length=200_000)
    title: str | None = Field(default=None, max_length=200)
    replace: bool = False
    language_hint: str | None = Field(default=None, max_length=16)

    @field_validator("script")
    @classmethod
    def strip_script(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("script must be at least 10 characters")
        return cleaned


class DocumentUploadMeta(BaseModel):
    """JSON-serializable upload acknowledgement fields (API §12.1)."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    source_type: str
    source_path: str
    source_hash: str
    size_bytes: int
    filename: str
    raw_content: RawContent
