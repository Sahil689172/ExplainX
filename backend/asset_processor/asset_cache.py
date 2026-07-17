"""SHA256 content-addressed cache for processed assets."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from asset_processor.exceptions import CacheError
from asset_processor.models import AssetMetadata


class AssetCache:
    """Skip reprocessing when a SHA256-matched result already exists."""

    def __init__(self, cache_directory: Path) -> None:
        self.cache_directory = Path(cache_directory)
        self.cache_directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise CacheError(f"Failed to hash file: {path}") from exc
        return digest.hexdigest()

    def entry_dir(self, digest: str) -> Path:
        return self.cache_directory / digest[:2] / digest

    def image_path(self, digest: str) -> Path:
        return self.entry_dir(digest) / "processed.png"

    def metadata_path(self, digest: str) -> Path:
        return self.entry_dir(digest) / "asset.json"

    def lookup(self, digest: str) -> AssetMetadata | None:
        meta_path = self.metadata_path(digest)
        image_path = self.image_path(digest)
        if not meta_path.is_file() or not image_path.is_file():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return AssetMetadata(
                original_filename=str(data["original_filename"]),
                processed_filename=str(data["processed_filename"]),
                hash=str(data["hash"]),
                width=int(data["width"]),
                height=int(data["height"]),
                channels=int(data.get("channels", 4)),
                transparent=bool(data["transparent"]),
                background_removed=bool(data["background_removed"]),
                processing_time_ms=float(data.get("processing_time_ms", 0.0)),
                created_at=str(data.get("created_at", "")),
                version=str(data.get("version", "4.6.0")),
                source_path=data.get("source_path"),
                processed_path=data.get("processed_path"),
                target_size=data.get("target_size"),
                cached=True,
            )
        except (OSError, KeyError, TypeError, ValueError):
            return None

    def store(self, digest: str, image_path: Path, metadata: AssetMetadata) -> Path:
        try:
            dest_dir = self.entry_dir(digest)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_image = self.image_path(digest)
            if image_path.resolve() != dest_image.resolve():
                shutil.copy2(image_path, dest_image)
            payload = metadata.to_dict()
            payload["hash"] = digest
            payload["processed_path"] = str(dest_image)
            self.metadata_path(digest).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return dest_image
        except OSError as exc:
            raise CacheError(f"Failed to write cache for {digest[:12]}") from exc
