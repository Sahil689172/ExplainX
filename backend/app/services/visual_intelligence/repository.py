"""AssetRepository — high-level API over the content-addressed AssetCache.

Provides querying and listing on top of :class:`AssetCache` without touching
the rendering engine. Callers use this to check for a reusable asset before
rendering and to register a freshly produced one afterwards.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.visual_intelligence.cache import AssetCache, compute_hash
from app.services.visual_intelligence.schemas import (
    AssetRecord,
    RendererType,
    RenderRequest,
)


class AssetRepository:
    """Query/registration facade for cached assets."""

    def __init__(self, cache: AssetCache | str | Path) -> None:
        self._cache = cache if isinstance(cache, AssetCache) else AssetCache(cache)

    @property
    def cache(self) -> AssetCache:
        return self._cache

    # ---- reuse-first API ------------------------------------------------- #

    def find(self, request: RenderRequest) -> AssetRecord | None:
        """Return an existing asset for this request, or ``None``."""
        return self._cache.lookup(request)

    def exists(self, request: RenderRequest) -> bool:
        return self._cache.has(compute_hash(request))

    def hash_for(self, request: RenderRequest) -> str:
        return compute_hash(request)

    def register(
        self,
        request: RenderRequest,
        *,
        png_path: str | Path,
        svg_path: str | Path | None = None,
        thumbnail_path: str | Path | None = None,
        generation_time_sec: float = 0.0,
        width: int | None = None,
        height: int | None = None,
    ) -> AssetRecord:
        """Store a freshly produced asset and return its record."""
        return self._cache.store(
            request,
            png_path=png_path,
            svg_path=svg_path,
            thumbnail_path=thumbnail_path,
            generation_time_sec=generation_time_sec,
            width=width,
            height=height,
        )

    def get(self, digest: str) -> AssetRecord | None:
        return self._cache.load(digest)

    # ---- introspection --------------------------------------------------- #

    def list_all(self) -> list[AssetRecord]:
        """Every asset currently in the cache (metadata only)."""
        records: list[AssetRecord] = []
        for meta in sorted(self._cache.cache_dir.rglob("metadata.json")):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                records.append(AssetRecord.model_validate(data))
            except (OSError, ValueError):
                continue
        return records

    def list_by_renderer(self, renderer: RendererType) -> list[AssetRecord]:
        return [r for r in self.list_all() if r.renderer == renderer]

    def stats(self) -> dict[str, object]:
        records = self.list_all()
        by_renderer: dict[str, int] = {}
        total_time = 0.0
        for r in records:
            by_renderer[r.renderer.value] = by_renderer.get(r.renderer.value, 0) + 1
            total_time += r.generation_time_sec
        return {
            "total_assets": len(records),
            "by_renderer": by_renderer,
            "total_generation_time_sec": round(total_time, 3),
            "cache_dir": str(self._cache.cache_dir),
        }
