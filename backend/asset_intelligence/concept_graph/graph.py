"""Concept Graph — educational concepts and relationships.

Architecture skeleton (Phase 4.7). In-memory reference implementation only.
No image generation.
"""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from asset_intelligence.schemas.concept import (
    ConceptGraphSnapshot,
    ConceptNode,
    ConceptRelation,
    RelationType,
)


class ConceptGraph:
    """In-memory concept graph conforming to ``ConceptGraphProtocol``."""

    def __init__(self) -> None:
        self._nodes: dict[UUID, ConceptNode] = {}
        self._by_name: dict[str, UUID] = {}
        self._relations: list[ConceptRelation] = []

    def upsert_node(self, node: ConceptNode) -> ConceptNode:
        key = node.normalized_name()
        existing_id = self._by_name.get(key)
        if existing_id is not None:
            existing = self._nodes[existing_id]
            existing.aliases = sorted(set(existing.aliases) | set(node.aliases))
            existing.tags = sorted(set(existing.tags) | set(node.tags))
            if node.description and not existing.description:
                existing.description = node.description
            return existing
        self._nodes[node.concept_id] = node
        self._by_name[key] = node.concept_id
        return node

    def add_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation: RelationType,
        *,
        weight: float = 1.0,
    ) -> ConceptRelation:
        if source_id not in self._nodes or target_id not in self._nodes:
            raise KeyError("Both source and target concepts must exist")
        edge = ConceptRelation(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
        )
        self._relations.append(edge)
        return edge

    def get_node(self, concept_id: UUID) -> ConceptNode | None:
        return self._nodes.get(concept_id)

    def find_by_name(self, name: str) -> ConceptNode | None:
        key = " ".join(name.strip().lower().split())
        cid = self._by_name.get(key)
        return self._nodes.get(cid) if cid else None

    def neighbors(
        self, concept_id: UUID, *, relation: RelationType | None = None
    ) -> Sequence[ConceptNode]:
        out: list[ConceptNode] = []
        for edge in self._relations:
            if edge.source_id != concept_id:
                continue
            if relation is not None and edge.relation != relation:
                continue
            node = self._nodes.get(edge.target_id)
            if node is not None:
                out.append(node)
        return out

    def snapshot_for_scene(
        self, *, project_id: str, scene_id: str, root_names: Sequence[str]
    ) -> ConceptGraphSnapshot:
        nodes: list[ConceptNode] = []
        for name in root_names:
            node = self.find_by_name(name)
            if node is None:
                node = self.upsert_node(ConceptNode(name=name))
            nodes.append(node)
        ids = {n.concept_id for n in nodes}
        relations = [
            e for e in self._relations if e.source_id in ids or e.target_id in ids
        ]
        root = nodes[0].concept_id if nodes else None
        return ConceptGraphSnapshot(
            nodes=list(nodes),
            relations=relations,
            root_concept_id=root,
            project_id=project_id,
            scene_id=scene_id,
        )
