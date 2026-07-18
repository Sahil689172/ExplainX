"""Asset Planner — reuse / generate / derive / reject (architecture skeleton)."""

from __future__ import annotations

from typing import Sequence

from asset_intelligence.interfaces.services import AssetLibraryProtocol
from asset_intelligence.schemas.asset import AssetCategory, AssetOntologyEntry
from asset_intelligence.schemas.concept import ConceptNode
from asset_intelligence.schemas.planner import (
    AssetDecision,
    AssetRequirement,
    PlannerDecisionKind,
    PlannerResult,
)


class AssetPlanner:
    """Decides how each concept visual is satisfied without generating images."""

    def __init__(self, library: AssetLibraryProtocol) -> None:
        self._library = library

    def plan_scene(
        self,
        *,
        scene_id: str,
        concepts: Sequence[ConceptNode],
        style_id: str,
    ) -> PlannerResult:
        decisions: list[AssetDecision] = []
        for concept in concepts:
            requirement = AssetRequirement(
                concept=concept,
                ontology=self._ontology_for(concept),
                style_id=style_id,
                scene_id=scene_id,
            )
            decisions.append(self.decide(requirement))
        return PlannerResult(scene_id=scene_id, decisions=decisions)

    def decide(self, requirement: AssetRequirement) -> AssetDecision:
        name = requirement.concept.name.strip()
        if not name:
            return AssetDecision(
                requirement=requirement,
                kind=PlannerDecisionKind.REJECT,
                reason="Empty concept name",
            )

        existing = self._library.find_reusable(
            semantic_name=name,
            style_id=requirement.style_id,
            concept=requirement.ontology.concept,
        )
        if existing is not None:
            self._library.increment_usage(existing.asset_id)
            return AssetDecision(
                requirement=requirement,
                kind=PlannerDecisionKind.REUSE,
                existing_asset=existing,
                reason="Semantic name + style match in Asset Library",
            )

        # Future: detect derive candidates (same concept, different view/style).
        # Phase 4.7 architecture: missing assets are marked GENERATE for later backends.
        return AssetDecision(
            requirement=requirement,
            kind=PlannerDecisionKind.GENERATE,
            reason="No reusable asset; queue for future ImageBackend",
        )

    @staticmethod
    def _ontology_for(concept: ConceptNode) -> AssetOntologyEntry:
        return AssetOntologyEntry(
            concept=concept.name,
            category=AssetCategory.OTHER,
            tags=list(concept.tags),
            difficulty=concept.difficulty,
            subject=concept.subject,
        )
