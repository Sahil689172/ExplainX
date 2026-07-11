"""Project API request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import (
    Difficulty,
    ProjectPhase,
    ProjectStatus,
    QualityProfile,
    SourceType,
)


class ProjectSettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_width: int = Field(default=1280, ge=320, le=3840)
    export_height: int = Field(default=720, ge=240, le=2160)
    fps: float = Field(default=30.0, gt=0, le=60)
    quality_profile: QualityProfile = QualityProfile.STANDARD
    burn_in_subtitles: bool = False
    subtitle_formats: list[str] = Field(default_factory=lambda: ["srt", "vtt"])
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    max_scenes: int | None = Field(default=None, ge=1, le=100)

    @field_validator("subtitle_formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        allowed = {"srt", "vtt"}
        cleaned = [v.lower().strip() for v in value]
        if not cleaned or any(v not in allowed for v in cleaned):
            raise ValueError("subtitle_formats must be a non-empty subset of srt,vtt")
        return cleaned


class ProjectSettingsPatch(BaseModel):
    """Partial settings update — only explicitly set fields are applied."""

    model_config = ConfigDict(extra="forbid")

    export_width: int | None = Field(default=None, ge=320, le=3840)
    export_height: int | None = Field(default=None, ge=240, le=2160)
    fps: float | None = Field(default=None, gt=0, le=60)
    quality_profile: QualityProfile | None = None
    burn_in_subtitles: bool | None = None
    subtitle_formats: list[str] | None = None
    speaking_rate: float | None = Field(default=None, ge=0.5, le=2.0)
    max_scenes: int | None = Field(default=None, ge=1, le=100)

    @field_validator("subtitle_formats")
    @classmethod
    def validate_formats(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        allowed = {"srt", "vtt"}
        cleaned = [v.lower().strip() for v in value]
        if not cleaned or any(v not in allowed for v in cleaned):
            raise ValueError("subtitle_formats must be a non-empty subset of srt,vtt")
        return cleaned


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    source_type: SourceType = SourceType.TOPIC
    source_topic: str | None = Field(default=None, max_length=500)
    theme_id: str = Field(default="notebooklm", min_length=1, max_length=64)
    source_language_code: str = Field(default="en", min_length=2, max_length=16)
    target_language_code: str = Field(default="en", min_length=2, max_length=16)
    voice_id: str | None = Field(default="en_US-lessac-medium", max_length=128)
    difficulty: Difficulty | None = Difficulty.INTERMEDIATE
    settings: ProjectSettingsIn = Field(default_factory=ProjectSettingsIn)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    theme_id: str | None = Field(default=None, min_length=1, max_length=64)
    voice_id: str | None = Field(default=None, max_length=128)
    difficulty: Difficulty | None = None
    target_language_code: str | None = Field(default=None, min_length=2, max_length=16)
    source_topic: str | None = Field(default=None, max_length=500)
    settings: ProjectSettingsPatch | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned


class ProjectRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned


class ProjectDuplicateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120)


class ProjectSettingsOut(BaseModel):
    export_width: int
    export_height: int
    fps: float
    quality_profile: str
    burn_in_subtitles: bool
    subtitle_formats: list[str]
    speaking_rate: float
    max_scenes: int | None = None


class ProjectSummary(BaseModel):
    project_id: str
    title: str
    description: str | None = None
    status: ProjectStatus
    current_phase: ProjectPhase
    theme_id: str
    source_language_code: str
    target_language_code: str
    updated_at: str
    created_at: str
    actual_duration_sec: float | None = None
    thumbnail_url: str | None = None


class ProjectDetail(ProjectSummary):
    source_type: SourceType
    source_topic: str | None = None
    source_path: str | None = None
    voice_id: str | None = None
    difficulty: str | None = None
    project_root: str
    assets_directory: str
    output_directory: str
    project_version: str
    dsl_version: str
    schema_version: str
    settings: ProjectSettingsOut
    directories: dict[str, str]
    configuration: dict[str, Any] = Field(default_factory=dict)


class ProjectListData(BaseModel):
    items: list[ProjectSummary]
    page: dict[str, Any]


class ExportManifest(BaseModel):
    project_id: str
    export_path: str
    files: list[dict[str, str]]
