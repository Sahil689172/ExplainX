"""Asset Planner decision schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from asset_intelligence.schemas.version import SCHEMA_VERSION
from asset_intelligence.schemas.asset import AssetOntologyEntry, AssetRecord
from asset_intelligence.schemas.concept import ConceptNode


class PlannerDecisionKind(str, Enum):
    """What the planner decides for one required visual."""

    REUSE = "reuse"
    GENERATE = "generate"
    DERIVE = "derive"
    REJECT = "reject"


@dataclass(slots=True)
class AssetRequirement:
    """A visual need extracted from a scene via concepts."""

    concept: ConceptNode
    ontology: AssetOntologyEntry
    style_id: str
    scene_id: str | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class AssetDecision:
    """Planner outcome for one requirement."""

    requirement: AssetRequirement
    kind: PlannerDecisionKind
    existing_asset: AssetRecord | None = None
    derive_from: UUID | None = None
    reason: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class PlannerResult:
    """Full plan for a scene: reuse vs generate vs derive."""

    scene_id: str
    decisions: list[AssetDecision]
    schema_version: str = SCHEMA_VERSION

    @property
    def to_generate(self) -> list[AssetDecision]:
        return [d for d in self.decisions if d.kind == PlannerDecisionKind.GENERATE]

    @property
    def to_reuse(self) -> list[AssetDecision]:
        return [d for d in self.decisions if d.kind == PlannerDecisionKind.REUSE]
