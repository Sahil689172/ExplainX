"""Phase 5.5 Educational Asset Repository models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = "1.0.0"
ASSET_KIND_IMAGE = "image"  # future: svg | model3d | animation | video


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class VersionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ConceptRecord:
    """One educational object (Earth, DNA, Volcano, …)."""

    concept_id: str
    title: str
    subject: str
    keywords: list[str] = field(default_factory=list)
    preferred_version: int | None = None
    approved_version_count: int = 0
    total_versions: int = 0
    last_updated: str = field(default_factory=utc_now_iso)
    slug: str = ""
    schema_version: str = SCHEMA_VERSION
    asset_kinds_supported: list[str] = field(
        default_factory=lambda: [ASSET_KIND_IMAGE, "svg", "model3d", "animation", "video"]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConceptRecord:
        known = {f.name for f in fields(cls)}
        payload = {k: v for k, v in data.items() if k in known}
        payload.setdefault("keywords", [])
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault(
            "asset_kinds_supported",
            [ASSET_KIND_IMAGE, "svg", "model3d", "animation", "video"],
        )
        return cls(**payload)


@dataclass
class VersionRecord:
    """One immutable generation of a concept."""

    id: str
    concept_id: str
    version: int
    title: str
    subject: str
    topic: str
    keywords: list[str]
    prompt: str
    enhanced_prompt: str
    generator: str
    model_version: str
    style: str
    background: str
    resolution: str
    generation_time_ms: float
    quality_score: float
    approved: bool
    preferred: bool
    status: str
    times_used: int
    last_used: str | None
    created_at: str
    file_path: str
    asset_kind: str = ASSET_KIND_IMAGE
    quality_details: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersionRecord:
        known = {f.name for f in fields(cls)}
        payload = {k: v for k, v in data.items() if k in known}
        payload.setdefault("keywords", [])
        payload.setdefault("quality_details", {})
        payload.setdefault("asset_kind", ASSET_KIND_IMAGE)
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("last_used", None)
        return cls(**payload)


@dataclass
class RepositoryStatistics:
    total_concepts: int = 0
    total_versions: int = 0
    approved_assets: int = 0
    rejected_assets: int = 0
    pending_review: int = 0
    average_quality: float = 0.0
    highest_quality_asset: str | None = None
    lowest_quality_asset: str | None = None
    most_used_asset: str | None = None
    least_used_asset: str | None = None
    cache_hits: int = 0
    cache_misses: int = 0
    generations_saved: int = 0
    average_lookup_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_uuid() -> str:
    return str(uuid4())


def slugify(title: str) -> str:
    import re

    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "concept"
