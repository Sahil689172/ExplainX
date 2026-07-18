"""ExplainX Asset Intelligence (Phase 4.7) — architecture layer.

This package defines the semantic bridge between Scene Planner and future
image-generation backends. It does **not** run inference or download models.

Pipeline position::

    Scene Planner
        → Concept Graph
        → Asset Planner
        → Asset Library / Prompt Generator
        → Image Backend (future)
        → Asset Processor (Phase 4.6)
        → Renderer
"""

from asset_intelligence.asset_library import AssetLibrary
from asset_intelligence.asset_planner import AssetPlanner
from asset_intelligence.concept_graph import ConceptGraph
from asset_intelligence.image_backend import NullImageBackend
from asset_intelligence.prompt_generator import PromptGenerator
from asset_intelligence.schemas.asset import AssetRecord, AssetScope
from asset_intelligence.schemas.concept import ConceptNode, ConceptRelation, RelationType
from asset_intelligence.schemas.planner import AssetDecision, PlannerDecisionKind
from asset_intelligence.schemas.prompt import PromptBundle
from asset_intelligence.schemas.style import StyleProfile
from asset_intelligence.style_system import StyleSystem

__all__ = [
    "AssetLibrary",
    "AssetPlanner",
    "ConceptGraph",
    "NullImageBackend",
    "PromptGenerator",
    "StyleSystem",
    "AssetRecord",
    "AssetScope",
    "ConceptNode",
    "ConceptRelation",
    "RelationType",
    "AssetDecision",
    "PlannerDecisionKind",
    "PromptBundle",
    "StyleProfile",
]
