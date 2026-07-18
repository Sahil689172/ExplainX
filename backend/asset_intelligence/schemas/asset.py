"""Asset ontology & library record schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from asset_intelligence.schemas.version import SCHEMA_VERSION


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssetCategory(str, Enum):
    """Top-level reusable asset categories (ontology)."""

    PLANET = "planet"
    ORGAN = "organ"
    CELL = "cell"
    NEURON = "neuron"
    BATTERY = "battery"
    MACHINE_PART = "machine_part"
    MOLECULE = "molecule"
    HISTORICAL_FIGURE = "historical_figure"
    MAP = "map"
    TIMELINE = "timeline"
    EQUATION = "equation"
    ICON = "icon"
    ARROW = "arrow"
    DIAGRAM = "diagram"
    BACKGROUND = "background"
    OTHER = "other"


class AssetScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    DERIVED = "derived"


class AssetView(str, Enum):
    FRONT = "front"
    SIDE = "side"
    TOP = "top"
    CROSS_SECTION = "cross_section"
    ISOMETRIC = "isometric"
    SCHEMATIC = "schematic"


@dataclass(slots=True)
class AssetOntologyEntry:
    """Describes *what kind* of thing an asset represents (not a file)."""

    concept: str
    category: AssetCategory
    subcategory: str | None = None
    tags: list[str] = field(default_factory=list)
    style_id: str | None = None
    view: AssetView = AssetView.FRONT
    difficulty: str | None = None
    subject: str | None = None
    dependencies: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class AssetRecord:
    """Source-of-truth library entry for one reusable visual asset."""

    semantic_name: str
    ontology: AssetOntologyEntry
    asset_id: UUID = field(default_factory=uuid4)
    scope: AssetScope = AssetScope.GLOBAL
    content_hash: str | None = None
    style_id: str | None = None
    file_path: str | None = None
    processed_path: str | None = None
    parent_asset_id: UUID | None = None  # for derived / variants
    variant_of: UUID | None = None
    version: str = "1"
    usage_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    schema_version: str = SCHEMA_VERSION
