"""Write ``{stem}.json`` metadata beside processed images."""

from __future__ import annotations

import json
from pathlib import Path

from asset_processor.models import AssetMetadata, utc_now_iso


class MetadataGenerator:
    """Build and persist asset metadata records."""

    def build(
        self,
        *,
        original_filename: str,
        processed_filename: str,
        digest: str,
        width: int,
        height: int,
        channels: int,
        transparent: bool,
        background_removed: bool,
        processing_time_ms: float,
        version: str,
        source_path: str | None = None,
        processed_path: str | None = None,
        target_size: int | None = None,
        cached: bool = False,
    ) -> AssetMetadata:
        return AssetMetadata(
            original_filename=original_filename,
            processed_filename=processed_filename,
            hash=digest,
            width=width,
            height=height,
            channels=channels,
            transparent=transparent,
            background_removed=background_removed,
            processing_time_ms=round(processing_time_ms, 2),
            created_at=utc_now_iso(),
            version=version,
            source_path=source_path,
            processed_path=processed_path,
            target_size=target_size,
            cached=cached,
        )

    def write(self, metadata: AssetMetadata, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path
