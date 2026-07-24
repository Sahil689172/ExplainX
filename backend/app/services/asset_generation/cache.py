"""Content-addressed cache for generated educational assets."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from app.services.asset_generation.models import (
    AssetFormat,
    AssetMetadata,
    AssetStatus,
    GeneratedAsset,
    GeneratorType,
)


def compute_plan_hash(
    *,
    scene_id: str,
    visual_type: str,
    renderer: str,
    style: str,
    theme: str,
    language: str,
    title: str = "",
    narration: str = "",
    keywords: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """SHA256 over ScenePlan identity + style/theme/language."""
    payload = {
        "scene_id": scene_id,
        "visual_type": visual_type,
        "renderer": renderer,
        "style": style,
        "theme": theme,
        "language": language,
        "title": title.strip(),
        "narration": narration.strip()[:500],
        "keywords": sorted(keywords or []),
        "extra": extra or {},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AssetGenerationCache:
    """Filesystem cache: ``<cache_dir>/<ab>/<hash>/``."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def entry_dir(self, digest: str) -> Path:
        return self.cache_dir / digest[:2] / digest

    def has(self, digest: str) -> bool:
        meta = self.entry_dir(digest) / "metadata.json"
        return meta.is_file()

    def lookup(self, digest: str) -> tuple[list[GeneratedAsset], AssetMetadata] | None:
        base = self.entry_dir(digest)
        meta_path = base / "metadata.json"
        if not meta_path.is_file():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            metadata = AssetMetadata.model_validate(data["metadata"])
            assets = [GeneratedAsset.model_validate(a) for a in data.get("assets", [])]
            # Rewrite paths relative to this entry (in case cache was moved).
            refreshed: list[GeneratedAsset] = []
            for asset in assets:
                name = Path(asset.path).name
                candidate = base / name
                path = str(candidate if candidate.is_file() else asset.path)
                refreshed.append(
                    asset.model_copy(
                        update={"path": path, "cache_hit": True, "status": AssetStatus.CACHED}
                    )
                )
            metadata = metadata.model_copy(update={"cache_hit": True})
            return refreshed, metadata
        except (OSError, ValueError, KeyError):
            return None

    def store(
        self,
        digest: str,
        *,
        assets: list[GeneratedAsset],
        metadata: AssetMetadata,
    ) -> list[GeneratedAsset]:
        base = self.entry_dir(digest)
        base.mkdir(parents=True, exist_ok=True)
        stored: list[GeneratedAsset] = []
        for asset in assets:
            src = Path(asset.path)
            if not src.is_file():
                continue
            dest = base / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            stored.append(asset.model_copy(update={"path": str(dest), "content_hash": digest}))

        payload = {
            "metadata": metadata.model_dump(mode="json"),
            "assets": [a.model_dump(mode="json") for a in stored],
        }
        (base / "metadata.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        # Convenience primary copies by format.
        for asset in stored:
            if asset.format == AssetFormat.PNG:
                thumb = base / "asset.png"
                if Path(asset.path).resolve() != thumb.resolve():
                    shutil.copy2(asset.path, thumb)
            if asset.format == AssetFormat.SVG:
                svg = base / "asset.svg"
                if Path(asset.path).resolve() != svg.resolve():
                    shutil.copy2(asset.path, svg)
        return stored
