"""Versioned data models for the Image Generation Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

SCHEMA_VERSION = "1.0.0"
ENGINE_VERSION = "5.2.0"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerationStatus(str, Enum):
    """Job lifecycle states (backend-independent)."""

    QUEUED = "queued"
    VALIDATING = "validating"
    SELECTING_BACKEND = "selecting_backend"
    GENERATING = "generating"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationMode(str, Enum):
    STANDARD = "standard"
    DRAFT = "draft"
    HIGH_QUALITY = "high_quality"


class OutputFormat(str, Enum):
    PNG = "png"
    WEBP = "webp"
    JPEG = "jpeg"


@dataclass(slots=True)
class GenerationMetadata:
    """Extensible metadata attached to requests, jobs, and responses."""

    entries: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def get(self, key: str, default: Any = None) -> Any:
        return self.entries.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.entries[key] = value


@dataclass(slots=True)
class GenerationRequest:
    """Inbound request accepted by ImageGenerationService."""

    prompt: str
    style_id: str
    width: int = 512
    height: int = 512
    aspect_ratio: str = "1:1"
    output_format: OutputFormat = OutputFormat.PNG
    mode: GenerationMode = GenerationMode.STANDARD
    negative_prompt: str = ""
    seed: int | None = None
    backend_id: str | None = None  # None → router chooses default
    priority: int = 0
    project_id: str | None = None
    scene_id: str | None = None
    asset_semantic_name: str | None = None
    request_id: UUID = field(default_factory=uuid4)
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    created_at: datetime = field(default_factory=_utc_now)
    schema_version: str = SCHEMA_VERSION
    version: str = ENGINE_VERSION


@dataclass(slots=True)
class GenerationProgress:
    """Progress snapshot for one job."""

    job_id: UUID
    status: GenerationStatus
    percent: float = 0.0
    message: str = ""
    backend_id: str | None = None
    updated_at: datetime = field(default_factory=_utc_now)
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    schema_version: str = SCHEMA_VERSION
    version: str = ENGINE_VERSION


@dataclass(slots=True)
class GenerationJob:
    """Tracked unit of work for one generation request."""

    request: GenerationRequest
    job_id: UUID = field(default_factory=uuid4)
    status: GenerationStatus = GenerationStatus.QUEUED
    backend_id: str | None = None
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 1
    error: str | None = None
    result_message: str | None = None
    output_path: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    schema_version: str = SCHEMA_VERSION
    version: str = ENGINE_VERSION

    @property
    def duration_ms(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds() * 1000.0


@dataclass(slots=True)
class GenerationResponse:
    """Standardized service response after a job completes (or fails)."""

    job_id: UUID
    request_id: UUID
    status: GenerationStatus
    backend_id: str | None = None
    message: str = ""
    output_path: str | None = None
    error: str | None = None
    duration_ms: float | None = None
    progress: GenerationProgress | None = None
    response_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utc_now)
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    schema_version: str = SCHEMA_VERSION
    version: str = ENGINE_VERSION


@dataclass(slots=True)
class BackendInfo:
    """Descriptor for a registered backend."""

    backend_id: str
    name: str
    version: str
    ready: bool = False
    supported_styles: list[str] = field(default_factory=list)
    supported_sizes: list[tuple[int, int]] = field(default_factory=list)
    is_default: bool = False
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    schema_version: str = SCHEMA_VERSION
    version_stamp: str = ENGINE_VERSION


@dataclass(slots=True)
class HealthStatus:
    """Engine-level health snapshot."""

    engine_ready: bool
    engine_version: str
    registered_backends: list[BackendInfo]
    queue_size: int
    pending_jobs: int
    completed_jobs: int
    failed_jobs: int
    default_backend_id: str | None = None
    message: str = ""
    checked_at: datetime = field(default_factory=_utc_now)
    health_id: UUID = field(default_factory=uuid4)
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    schema_version: str = SCHEMA_VERSION
    version: str = ENGINE_VERSION


@dataclass(slots=True)
class BackendGenerateResult:
    """Result returned by ImageBackend.generate (no pixels in Phase 5.1)."""

    success: bool
    message: str
    output_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
