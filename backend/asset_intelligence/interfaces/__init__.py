"""Protocols / interfaces for Asset Intelligence (dependency inversion)."""

from asset_intelligence.interfaces.image_backend import ImageBackend
from asset_intelligence.interfaces.caches import (
    AssetCacheProtocol,
    ConceptCacheProtocol,
    GenerationCacheProtocol,
    PromptCacheProtocol,
    StyleCacheProtocol,
)
from asset_intelligence.interfaces.services import (
    AssetLibraryProtocol,
    AssetPlannerProtocol,
    ConceptGraphProtocol,
    PromptGeneratorProtocol,
    StyleSystemProtocol,
)

__all__ = [
    "ImageBackend",
    "AssetCacheProtocol",
    "ConceptCacheProtocol",
    "GenerationCacheProtocol",
    "PromptCacheProtocol",
    "StyleCacheProtocol",
    "AssetLibraryProtocol",
    "AssetPlannerProtocol",
    "ConceptGraphProtocol",
    "PromptGeneratorProtocol",
    "StyleSystemProtocol",
]
