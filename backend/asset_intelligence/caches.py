"""In-memory multi-layer caches — independently invalidatable."""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from asset_intelligence.schemas.asset import AssetRecord
from asset_intelligence.schemas.concept import ConceptGraphSnapshot, ConceptNode
from asset_intelligence.schemas.prompt import GenerationResult, PromptBundle
from asset_intelligence.schemas.style import StyleProfile

T = TypeVar("T")


class _LayerCache(Generic[T]):
    """Simple key→value store with full or keyed invalidation."""

    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    def _get(self, key: str) -> T | None:
        return self._store.get(key)

    def _put(self, key: str, value: T) -> None:
        self._store[key] = value

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)


class ConceptCache(_LayerCache[ConceptNode | ConceptGraphSnapshot]):
    def get(self, key: str) -> ConceptNode | ConceptGraphSnapshot | None:
        return self._get(key)

    def put(self, key: str, value: ConceptNode | ConceptGraphSnapshot) -> None:
        self._put(key, value)


class AssetCache:
    def __init__(self) -> None:
        self._by_id: dict[UUID, AssetRecord] = {}
        self._by_hash: dict[str, AssetRecord] = {}

    def get_by_hash(self, content_hash: str) -> AssetRecord | None:
        return self._by_hash.get(content_hash)

    def get_by_id(self, asset_id: UUID) -> AssetRecord | None:
        return self._by_id.get(asset_id)

    def put(self, record: AssetRecord) -> None:
        self._by_id[record.asset_id] = record
        if record.content_hash:
            self._by_hash[record.content_hash] = record

    def invalidate(self, key: str | UUID | None = None) -> None:
        if key is None:
            self._by_id.clear()
            self._by_hash.clear()
            return
        if isinstance(key, UUID):
            record = self._by_id.pop(key, None)
            if record and record.content_hash:
                self._by_hash.pop(record.content_hash, None)
            return
        record = self._by_hash.pop(key, None)
        if record:
            self._by_id.pop(record.asset_id, None)


class PromptCache(_LayerCache[PromptBundle]):
    def get(self, key: str) -> PromptBundle | None:
        return self._get(key)

    def put(self, key: str, prompt: PromptBundle) -> None:
        self._put(key, prompt)


class StyleCache(_LayerCache[StyleProfile]):
    def get(self, style_id: str) -> StyleProfile | None:
        return self._get(style_id)

    def put(self, profile: StyleProfile) -> None:
        self._put(profile.style_id, profile)

    def invalidate(self, style_id: str | None = None) -> None:
        super().invalidate(style_id)


class GenerationCache(_LayerCache[GenerationResult]):
    def get(self, prompt_hash: str) -> GenerationResult | None:
        return self._get(prompt_hash)

    def put(self, prompt_hash: str, result: GenerationResult) -> None:
        self._put(prompt_hash, result)
