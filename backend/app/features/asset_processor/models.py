"""Asset processing models (Phase 4.6)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AssetMetadata(BaseModel):
    """Persisted beside each processed asset as ``asset.json``."""

    original_filename: str
    processed_filename: str
    width: int
    height: int
    hash: str
    transparent: bool
    processing_date: str = Field(default_factory=utc_now_iso)
    background_removed: bool = True
    target_size: int | None = None
    source_path: str | None = None
    processed_path: str | None = None


class ProcessResult(BaseModel):
    """Return value of ``AssetProcessor.process``."""

    processed_path: Path
    metadata: AssetMetadata
    cached: bool = False
