"""ExplainX Asset Generation Engine — ScenePlan → deterministic visual assets.

Public API::

    from app.services.asset_generation import AssetGenerationService

    service = AssetGenerationService.with_cache(cache_dir)
    bundle = service.generate(scene_plan, output_dir=..., export_dir=...)

Integrates with Visual Intelligence without modifying its API. No cloud APIs,
no LLM calls, no AI image generation (``LocalImageGenerator`` is interface-only).
"""

from __future__ import annotations

from app.services.asset_generation.cache import AssetGenerationCache, compute_plan_hash
from app.services.asset_generation.exporter import AssetExporter
from app.services.asset_generation.interfaces import AssetGenerator
from app.services.asset_generation.models import (
    GENERATOR_PRIORITY,
    AssetBundle,
    AssetFormat,
    AssetMetadata,
    AssetStatus,
    AssetType,
    GeneratedAsset,
    GenerationResult,
    GeneratorType,
    ScenePackage,
)
from app.services.asset_generation.registry import GeneratorRegistry, default_registry
from app.services.asset_generation.scene_composer import SceneComposer
from app.services.asset_generation.service import AssetGenerationService
from app.services.asset_generation.validator import AssetValidator

__all__ = [
    "GENERATOR_PRIORITY",
    "AssetBundle",
    "AssetExporter",
    "AssetFormat",
    "AssetGenerationCache",
    "AssetGenerationService",
    "AssetGenerator",
    "AssetMetadata",
    "AssetStatus",
    "AssetType",
    "AssetValidator",
    "GeneratedAsset",
    "GenerationResult",
    "GeneratorRegistry",
    "GeneratorType",
    "SceneComposer",
    "ScenePackage",
    "compute_plan_hash",
    "default_registry",
]
