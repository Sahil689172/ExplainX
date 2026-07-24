"""Generator base re-export (plugin contract lives in interfaces)."""

from __future__ import annotations

from app.services.asset_generation.interfaces import AssetGenerator

__all__ = ["AssetGenerator"]
