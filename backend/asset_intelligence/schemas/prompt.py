"""Prompt & generation request schemas — architecture only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from asset_intelligence.schemas.version import SCHEMA_VERSION
from asset_intelligence.schemas.planner import AssetRequirement
from asset_intelligence.schemas.style import StyleProfile


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PromptBundle:
    """WHAT (subject) + HOW (style) assembled for a missing asset only."""

    requirement: AssetRequirement
    style: StyleProfile
    positive_prompt: str
    negative_prompt: str
    prompt_id: UUID = field(default_factory=uuid4)
    seed: int | None = None
    width: int = 512
    height: int = 512
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(slots=True)
class GenerationRequest:
    """Request handed to an ImageBackend — no model code here."""

    prompt: PromptBundle
    request_id: UUID = field(default_factory=uuid4)
    backend_id: str = "unspecified"
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class GenerationResult:
    """Future backend output contract."""

    request_id: UUID
    status: GenerationStatus
    output_path: str | None = None
    error: str | None = None
    backend_id: str = "unspecified"
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
