"""Persistent asset index — UUID-keyed catalog (never depend on filenames)."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import UUID, uuid4

SCHEMA_VERSION = "1.0.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class AssetMetadata:
    """On-disk metadata for one library asset."""

    id: str
    title: str
    category: str
    keywords: list[str]
    style: str
    background: str
    width: int
    height: int
    created_at: str
    generator: str
    prompt: str
    enhanced_prompt: str
    file_path: str
    metadata_path: str | None = None
    schema_version: str = SCHEMA_VERSION
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetMetadata:
        known = {
            "id",
            "title",
            "category",
            "keywords",
            "style",
            "background",
            "width",
            "height",
            "created_at",
            "generator",
            "prompt",
            "enhanced_prompt",
            "file_path",
            "metadata_path",
            "schema_version",
            "extra",
        }
        payload = {k: v for k, v in data.items() if k in known}
        payload.setdefault("extra", {})
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("metadata_path", None)
        return cls(**payload)


@dataclass
class AssetIndexStats:
    total_assets: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    generation_saved: int = 0
    average_lookup_ms: float = 0.0
    _lookup_total_ms: float = 0.0
    _lookup_count: int = 0

    def record_lookup(self, *, hit: bool, elapsed_ms: float) -> None:
        if hit:
            self.cache_hits += 1
            self.generation_saved += 1
        else:
            self.cache_misses += 1
        self._lookup_total_ms += elapsed_ms
        self._lookup_count += 1
        self.average_lookup_ms = (
            self._lookup_total_ms / self._lookup_count if self._lookup_count else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_assets": self.total_assets,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "generation_saved": self.generation_saved,
            "average_lookup_ms": round(self.average_lookup_ms, 3),
        }


class AssetIndex:
    """In-memory index mirrored to ``metadata/_index.json``."""

    def __init__(self, index_path: Path) -> None:
        self._path = index_path
        self._lock = threading.RLock()
        self._by_id: dict[str, AssetMetadata] = {}
        self.stats = AssetIndexStats()
        self.reload()

    def reload(self) -> None:
        with self._lock:
            self._by_id.clear()
            if not self._path.is_file():
                self.stats.total_assets = 0
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            assets = raw.get("assets", [])
            for item in assets:
                meta = AssetMetadata.from_dict(item)
                self._by_id[meta.id] = meta
            self.stats.total_assets = len(self._by_id)
            saved = raw.get("stats")
            if isinstance(saved, dict):
                self.stats.cache_hits = int(saved.get("cache_hits", 0))
                self.stats.cache_misses = int(saved.get("cache_misses", 0))
                self.stats.generation_saved = int(saved.get("generation_saved", 0))
                self.stats.average_lookup_ms = float(
                    saved.get("average_lookup_ms", 0.0)
                )

    def persist(self) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "updated_at": _utc_now_iso(),
                "stats": self.stats.to_dict(),
                "assets": [m.to_dict() for m in self._by_id.values()],
            }
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._path)

    def get(self, asset_id: str | UUID) -> AssetMetadata | None:
        return self._by_id.get(str(asset_id))

    def all(self) -> Sequence[AssetMetadata]:
        return list(self._by_id.values())

    def add(self, meta: AssetMetadata) -> AssetMetadata:
        with self._lock:
            if meta.id in self._by_id:
                raise ValueError(f"Asset id already indexed: {meta.id}")
            self._by_id[meta.id] = meta
            self.stats.total_assets = len(self._by_id)
            self.persist()
            return meta

    @staticmethod
    def new_id() -> str:
        return str(uuid4())
