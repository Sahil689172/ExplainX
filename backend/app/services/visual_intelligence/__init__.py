"""ExplainX Visual Intelligence — hybrid educational visual generation.

This package decides *what* visual each scene needs and *which* renderer should
produce it, caches generated assets by content hash, and models multi-layer
scene composition. It never renders pixels itself and never calls an LLM (yet);
classification is deterministic and rule-based, with prompt templates prepared
for a future LLM upgrade.

Public API::

    from app.services.visual_intelligence import (
        VisualIntelligenceService,
        VisualIntentAnalyzer,
        VisualAssetRouter,
        AssetCache,
        AssetRepository,
        RendererRegistry,
        LayeredSceneComposer,
    )

The service is additive: existing phases (Scene Composer, Timeline Engine,
rendering engines) are untouched. See ``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

from app.services.visual_intelligence.asset_router import (
    RouterConfig,
    VisualAssetRouter,
)
from app.services.visual_intelligence.cache import AssetCache
from app.services.visual_intelligence.intent_analyzer import VisualIntentAnalyzer
from app.services.visual_intelligence.layers import (
    LayeredScene,
    LayeredSceneComposer,
    VisualLayer,
)
from app.services.visual_intelligence.pipeline_adapter import (
    plan_script,
    plan_script_as_dicts,
    script_to_scene_inputs,
)
from app.services.visual_intelligence.renderers import (
    RendererPlugin,
    RendererRegistry,
    default_registry,
)
from app.services.visual_intelligence.repository import AssetRepository
from app.services.visual_intelligence.schemas import (
    AssetRecord,
    Complexity,
    LayerType,
    RendererType,
    RenderingStrategy,
    RenderRequest,
    SceneInput,
    VisualIntent,
    VisualType,
)
from app.services.visual_intelligence.service import ScenePlan, VisualIntelligenceService

__all__ = [
    "AssetCache",
    "AssetRecord",
    "AssetRepository",
    "Complexity",
    "LayerType",
    "LayeredScene",
    "LayeredSceneComposer",
    "RendererPlugin",
    "RendererRegistry",
    "RendererType",
    "RenderRequest",
    "RenderingStrategy",
    "RouterConfig",
    "ScenePlan",
    "SceneInput",
    "VisualAssetRouter",
    "VisualIntent",
    "VisualIntentAnalyzer",
    "VisualIntelligenceService",
    "VisualLayer",
    "VisualType",
    "default_registry",
    "plan_script",
    "plan_script_as_dicts",
    "script_to_scene_inputs",
]
