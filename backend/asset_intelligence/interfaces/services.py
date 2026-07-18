"""Service protocols for Concept Graph, Library, Planner, Prompts, Styles."""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable
from uuid import UUID

from asset_intelligence.schemas.asset import AssetRecord
from asset_intelligence.schemas.concept import (
    ConceptGraphSnapshot,
    ConceptNode,
    ConceptRelation,
    RelationType,
)
from asset_intelligence.schemas.planner import AssetDecision, AssetRequirement, PlannerResult
from asset_intelligence.schemas.prompt import PromptBundle
from asset_intelligence.schemas.style import StyleProfile


@runtime_checkable
class ConceptGraphProtocol(Protocol):
    """Understands educational concepts and relationships."""

    def upsert_node(self, node: ConceptNode) -> ConceptNode: ...

    def add_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation: RelationType,
        *,
        weight: float = 1.0,
    ) -> ConceptRelation: ...

    def get_node(self, concept_id: UUID) -> ConceptNode | None: ...

    def find_by_name(self, name: str) -> ConceptNode | None: ...

    def neighbors(
        self, concept_id: UUID, *, relation: RelationType | None = None
    ) -> Sequence[ConceptNode]: ...

    def snapshot_for_scene(
        self, *, project_id: str, scene_id: str, root_names: Sequence[str]
    ) -> ConceptGraphSnapshot: ...


@runtime_checkable
class AssetLibraryProtocol(Protocol):
    """Source of truth for reusable assets — no duplicates by hash/semantics."""

    def get(self, asset_id: UUID) -> AssetRecord | None: ...

    def find_reusable(
        self,
        *,
        semantic_name: str,
        style_id: str,
        concept: str | None = None,
    ) -> AssetRecord | None: ...

    def register(self, record: AssetRecord) -> AssetRecord: ...

    def increment_usage(self, asset_id: UUID) -> None: ...

    def list_variants(self, asset_id: UUID) -> Sequence[AssetRecord]: ...


@runtime_checkable
class StyleSystemProtocol(Protocol):
    """Loads and resolves style profiles from JSON (never hardcodes prompts)."""

    def get(self, style_id: str) -> StyleProfile: ...

    def list_styles(self) -> Sequence[StyleProfile]: ...

    def reload(self) -> None: ...


@runtime_checkable
class AssetPlannerProtocol(Protocol):
    """Decides reuse / generate / derive / reject per concept requirement."""

    def plan_scene(
        self,
        *,
        scene_id: str,
        concepts: Sequence[ConceptNode],
        style_id: str,
    ) -> PlannerResult: ...

    def decide(self, requirement: AssetRequirement) -> AssetDecision: ...


@runtime_checkable
class PromptGeneratorProtocol(Protocol):
    """Builds prompts only for missing assets — WHAT separate from HOW."""

    def generate(self, decision: AssetDecision, style: StyleProfile) -> PromptBundle: ...

    def generate_many(
        self, decisions: Sequence[AssetDecision], style: StyleProfile
    ) -> Sequence[PromptBundle]: ...
