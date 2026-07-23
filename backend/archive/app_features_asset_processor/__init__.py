"""ExplainX Asset Processing Pipeline (Phase 4.6).

Prepares images before they reach the renderer:

    raw → background removal → resize → normalize → validate → metadata → cache
"""

from app.features.asset_processor.asset_pipeline import AssetProcessor
from app.features.asset_processor.models import AssetMetadata, ProcessResult

__all__ = ["AssetProcessor", "AssetMetadata", "ProcessResult"]
