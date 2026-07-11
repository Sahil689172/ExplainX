"""HTTP request/response models for Input Intelligence (Phase 2.1 / 2.2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.artifacts.raw_content import RawContent


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
