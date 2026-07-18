"""Concept Graph schemas — educational concepts, not pixels."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from asset_intelligence.schemas.version import SCHEMA_VERSION


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RelationType(str, Enum):
    """Canonical semantic edges between concepts."""

    IS_A = "IS_A"
    PART_OF = "PART_OF"
    CONTAINS = "CONTAINS"
    ORBITS = "ORBITS"
    CAUSES = "CAUSES"
    RELATED_TO = "RELATED_TO"
    OPPOSITE_OF = "OPPOSITE_OF"
    INSTANCE_OF = "INSTANCE_OF"
    REQUIRES = "REQUIRES"
    ILLUSTRATES = "ILLUSTRATES"


@dataclass(slots=True)
class ConceptNode:
    """One educational concept in the graph."""

    name: str
    concept_id: UUID = field(default_factory=uuid4)
    aliases: list[str] = field(default_factory=list)
    subject: str | None = None
    difficulty: str | None = None  # beginner | intermediate | advanced
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)

    def normalized_name(self) -> str:
        return " ".join(self.name.strip().lower().split())


@dataclass(slots=True)
class ConceptRelation:
    """Directed edge: source --type--> target."""

    source_id: UUID
    target_id: UUID
    relation: RelationType
    relation_id: UUID = field(default_factory=uuid4)
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class ConceptGraphSnapshot:
    """Immutable snapshot of a concept subgraph for a scene/project."""

    nodes: list[ConceptNode]
    relations: list[ConceptRelation]
    root_concept_id: UUID | None = None
    project_id: str | None = None
    scene_id: str | None = None
    schema_version: str = SCHEMA_VERSION
