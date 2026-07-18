"""Project-level Asset Intelligence metadata schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from asset_intelligence.schemas.version import SCHEMA_VERSION


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ProjectAssetPlan:
    """Aggregated plan metadata for one project."""

    project_id: str
    default_style_id: str
    scene_ids: list[str] = field(default_factory=list)
    asset_ids: list[UUID] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
