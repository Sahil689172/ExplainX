"""Data models for the Asset Processing Pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class AssetMetadata:
    """Persisted beside each processed asset as ``{stem}.json``."""

    original_filename: str
    processed_filename: str
    hash: str
    width: int
    height: int
    channels: int
    transparent: bool
    background_removed: bool
    processing_time_ms: float
    created_at: str = field(default_factory=utc_now_iso)
    version: str = "4.6.0"
    source_path: str | None = None
    processed_path: str | None = None
    target_size: int | None = None
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProcessedAsset:
    """Return value of ``AssetProcessor.process``."""

    processed_path: Path
    metadata: AssetMetadata
    processing_time: float  # seconds
    cached: bool = False
