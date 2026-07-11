"""Unified RawContent artifact — Phase 2.1 / 2.2 Input Intelligence output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
