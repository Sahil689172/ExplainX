"""Asset Library — source of truth for reusable assets (no duplicates)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from asset_intelligence.schemas.asset import AssetRecord, AssetScope


class AssetLibrary:
    """In-memory library conforming to ``AssetLibraryProtocol``."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, AssetRecord] = {}
        self._by_hash: dict[str, UUID] = {}
        self._by_semantic: dict[tuple[str, str], UUID] = {}

    def get(self, asset_id: UUID) -> AssetRecord | None:
        return self._by_id.get(asset_id)

    def find_reusable(
        self,
        *,
        semantic_name: str,
        style_id: str,
        concept: str | None = None,
    ) -> AssetRecord | None:
        key = (semantic_name.strip().lower(), style_id)
        aid = self._by_semantic.get(key)
        if aid is None:
            return None
        record = self._by_id[aid]
        if concept and record.ontology.concept.lower() != concept.lower():
            return None
        return record

    def register(self, record: AssetRecord) -> AssetRecord:
        if record.content_hash and record.content_hash in self._by_hash:
            return self._by_id[self._by_hash[record.content_hash]]

        style = record.style_id or record.ontology.style_id or "default"
        key = (record.semantic_name.strip().lower(), style)
        existing = self._by_semantic.get(key)
        if existing is not None:
            return self._by_id[existing]

        self._by_id[record.asset_id] = record
        if record.content_hash:
            self._by_hash[record.content_hash] = record.asset_id
        self._by_semantic[key] = record.asset_id
        return record

    def increment_usage(self, asset_id: UUID) -> None:
        record = self._by_id[asset_id]
        record.usage_count += 1
        record.updated_at = datetime.now(timezone.utc)

    def list_variants(self, asset_id: UUID) -> Sequence[AssetRecord]:
        return [
            r
            for r in self._by_id.values()
            if r.variant_of == asset_id or r.parent_asset_id == asset_id
        ]

    def list_by_scope(self, scope: AssetScope) -> Sequence[AssetRecord]:
        return [r for r in self._by_id.values() if r.scope == scope]
