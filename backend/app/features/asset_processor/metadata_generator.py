"""Write ``asset.json`` metadata beside processed images."""

from __future__ import annotations

import json
from pathlib import Path

from app.features.asset_processor.models import AssetMetadata, utc_now_iso


class MetadataGenerator:
    """Build and persist asset metadata records."""

    def build(
        self,
        *,
        original_filename: str,
        processed_filename: str,
        width: int,
        height: int,
        digest: str,
        transparent: bool,
        background_removed: bool,
        target_size: int | None = None,
        source_path: str | None = None,
        processed_path: str | None = None,
    ) -> AssetMetadata:
        return AssetMetadata(
            original_filename=original_filename,
            processed_filename=processed_filename,
            width=width,
            height=height,
            hash=digest,
            transparent=transparent,
            processing_date=utc_now_iso(),
            background_removed=background_removed,
            target_size=target_size,
            source_path=source_path,
            processed_path=processed_path,
        )

    def write(self, metadata: AssetMetadata, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(metadata.model_dump(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path
