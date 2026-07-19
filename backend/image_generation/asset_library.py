"""Filesystem Smart Asset Library — PNG + metadata JSON (never overwrite)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Sequence

from image_generation.asset_index import AssetIndex, AssetMetadata, _utc_now_iso
from image_generation.keyword_expand import expand_from_prompt, normalize_token
from image_generation.logger import GenerationJobLogger


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent


class SmartAssetLibrary:
    """Source of truth for reusable generated educational assets on disk."""

    def __init__(
        self,
        *,
        root: Path | None = None,
        logger: GenerationJobLogger | None = None,
    ) -> None:
        self.root = (root or (_backend_root() / "asset_library")).resolve()
        self.assets_dir = self.root / "assets"
        self.metadata_dir = self.root / "metadata"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.index = AssetIndex(self.metadata_dir / "_index.json")
        self._logger = logger or GenerationJobLogger()
        self._sync_from_disk()

    def _sync_from_disk(self) -> None:
        """Load any metadata JSON files not yet in the index."""
        for path in sorted(self.metadata_dir.glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                meta = AssetMetadata.from_dict(data)
            except (OSError, json.JSONDecodeError, TypeError, KeyError):
                continue
            if self.index.get(meta.id) is None:
                try:
                    self.index.add(meta)
                except ValueError:
                    pass

    def list_assets(self) -> Sequence[AssetMetadata]:
        return self.index.all()

    def get(self, asset_id: str) -> AssetMetadata | None:
        return self.index.get(asset_id)

    def resolve_file(self, meta: AssetMetadata) -> Path:
        path = Path(meta.file_path)
        if not path.is_absolute():
            path = _backend_root() / path
        return path.resolve()

    def save_new_asset(
        self,
        *,
        source_png: Path,
        title: str,
        prompt: str,
        enhanced_prompt: str,
        style: str = "flat_vector",
        category: str = "General",
        background: str = "transparent",
        width: int = 512,
        height: int = 512,
        generator: str = "OpenVINO SD1.5",
        keywords: list[str] | None = None,
    ) -> AssetMetadata:
        """Copy PNG into library and write metadata. Never overwrites existing files."""
        source_png = Path(source_png)
        if not source_png.is_file():
            raise FileNotFoundError(f"Source PNG missing: {source_png}")

        asset_id = AssetIndex.new_id()
        # Filenames are UUID-based — titles live in metadata only.
        asset_filename = f"{asset_id}.png"
        dest_png = self.assets_dir / asset_filename
        if dest_png.exists():
            # Astronomically unlikely; regenerate id once
            asset_id = AssetIndex.new_id()
            asset_filename = f"{asset_id}.png"
            dest_png = self.assets_dir / asset_filename

        shutil.copy2(source_png, dest_png)

        keys = keywords or expand_from_prompt(prompt, title=title)
        if normalize_token(title) not in {normalize_token(k) for k in keys}:
            keys = [normalize_token(title), *keys]

        rel_file = f"asset_library/assets/{asset_filename}"
        meta_path = self.metadata_dir / f"{asset_id}.json"
        meta = AssetMetadata(
            id=asset_id,
            title=title.strip() or "Untitled",
            category=category,
            keywords=sorted({normalize_token(k) for k in keys if normalize_token(k)}),
            style=style,
            background=background,
            width=width,
            height=height,
            created_at=_utc_now_iso(),
            generator=generator,
            prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            file_path=rel_file,
            metadata_path=f"asset_library/metadata/{asset_id}.json",
        )
        meta_path.write_text(json.dumps(meta.to_dict(), indent=2), encoding="utf-8")
        self.index.add(meta)
        self._logger.info(
            "ASSET_SAVED",
            asset_id=asset_id,
            title=meta.title,
            path=rel_file,
        )
        return meta
