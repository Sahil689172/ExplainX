"""Asset search — keyword now, embeddings later (swap one module)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from image_generation.asset_index import AssetMetadata
from image_generation.keyword_expand import expand_keywords, normalize_token


@dataclass(slots=True)
class SearchQuery:
    text: str
    title: str | None = None
    keywords: list[str] | None = None
    style: str | None = None


@dataclass(slots=True)
class SearchHit:
    asset: AssetMetadata
    score: float
    match_kind: str  # exact_title | exact_keyword | similar_keyword | embedding


class AssetSearcher(ABC):
    """Future-ready search interface (keyword or embedding)."""

    @abstractmethod
    def search(self, query: SearchQuery, *, limit: int = 5) -> Sequence[SearchHit]:
        ...


class KeywordSearcher(AssetSearcher):
    """Exact title → exact keyword → similar / expanded keyword."""

    def __init__(self, assets: Sequence[AssetMetadata] | None = None) -> None:
        self._assets: list[AssetMetadata] = list(assets or [])

    def set_assets(self, assets: Sequence[AssetMetadata]) -> None:
        self._assets = list(assets)

    def search(self, query: SearchQuery, *, limit: int = 5) -> Sequence[SearchHit]:
        title = normalize_token(query.title or query.text)
        q_keywords = {
            normalize_token(k)
            for k in (query.keywords or expand_keywords([query.text, title or ""]))
            if normalize_token(k)
        }
        if title:
            q_keywords.add(title)

        hits: list[SearchHit] = []

        # 1. Exact title
        for asset in self._assets:
            if normalize_token(asset.title) == title and title:
                hits.append(SearchHit(asset=asset, score=100.0, match_kind="exact_title"))

        # 2. Exact keyword
        for asset in self._assets:
            if any(h.asset.id == asset.id for h in hits):
                continue
            asset_keys = {normalize_token(k) for k in asset.keywords}
            if title and title in asset_keys:
                hits.append(
                    SearchHit(asset=asset, score=90.0, match_kind="exact_keyword")
                )

        # 3. Similar / expanded keyword overlap
        for asset in self._assets:
            if any(h.asset.id == asset.id for h in hits):
                continue
            asset_keys = {normalize_token(k) for k in asset.keywords}
            expanded_asset = set(expand_keywords(asset_keys | {asset.title}))
            overlap = q_keywords & (asset_keys | expanded_asset)
            if not overlap:
                continue
            score = 50.0 + 5.0 * len(overlap)
            hits.append(
                SearchHit(asset=asset, score=score, match_kind="similar_keyword")
            )

        if query.style:
            style = normalize_token(query.style)
            hits = [
                h
                for h in hits
                if normalize_token(h.asset.style) == style
                or style in normalize_token(h.asset.style)
            ] or hits

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]


class EmbeddingSearcher(AssetSearcher):
    """Placeholder for future vector search — swap in without changing AssetManager."""

    def __init__(self) -> None:
        self._enabled = False

    def search(self, query: SearchQuery, *, limit: int = 5) -> Sequence[SearchHit]:
        # Not implemented in Phase 5.4 — returns empty so KeywordSearcher remains primary.
        return []
