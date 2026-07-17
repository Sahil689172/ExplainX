"""ExplainX Asset Processing Pipeline (Phase 4.6).

Official gateway for all image assets before they reach the renderer.

Example::

    from asset_processor import AssetProcessor

    processor = AssetProcessor()
    result = processor.process("raw_assets/earth.jpg")
    print(result.processed_path, result.cached)
"""

from asset_processor.asset_pipeline import AssetProcessor
from asset_processor.config import AssetProcessorConfig
from asset_processor.exceptions import (
    AssetProcessorError,
    BackgroundRemovalError,
    CacheError,
    ImageLoadError,
    ValidationError,
)
from asset_processor.models import AssetMetadata, ProcessedAsset

__all__ = [
    "AssetProcessor",
    "AssetProcessorConfig",
    "AssetMetadata",
    "ProcessedAsset",
    "AssetProcessorError",
    "ImageLoadError",
    "BackgroundRemovalError",
    "ValidationError",
    "CacheError",
]
