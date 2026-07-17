"""SHA256 cache for processed assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.features.asset_processor.models import AssetMetadata


class AssetCache:
    """Content-addressed cache under ``cache/``."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def entry_dir(self, digest: str) -> Path:
        return self.cache_dir / digest[:2] / digest

    def processed_image_path(self, digest: str) -> Path:
        return self.entry_dir(digest) / "processed.png"

    def metadata_path(self, digest: str) -> Path:
        return self.entry_dir(digest) / "asset.json"

    def lookup(self, digest: str) -> AssetMetadata | None:
        meta_path = self.metadata_path(digest)
        image_path = self.processed_image_path(digest)
        if not meta_path.is_file() or not image_path.is_file():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return AssetMetadata.model_validate(data)
        except (OSError, ValueError):
            return None

    def store(self, digest: str, image_path: Path, metadata: AssetMetadata) -> Path:
        """Copy processed image + metadata into the cache; return cached image path."""
        import shutil

        dest_dir = self.entry_dir(digest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_image = self.processed_image_path(digest)
        if image_path.resolve() != dest_image.resolve():
            shutil.copy2(image_path, dest_image)
        meta = metadata.model_copy(
            update={
                "hash": digest,
                "processed_path": str(dest_image),
            }
        )
        self.metadata_path(digest).write_text(
            meta.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        return dest_image
