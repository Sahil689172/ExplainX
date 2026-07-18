"""Composition root helpers — dependency injection without frameworks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from asset_intelligence.asset_library import AssetLibrary
from asset_intelligence.asset_planner import AssetPlanner
from asset_intelligence.caches import (
    AssetCache,
    ConceptCache,
    GenerationCache,
    PromptCache,
    StyleCache,
)
from asset_intelligence.concept_graph import ConceptGraph
from asset_intelligence.image_backend import NullImageBackend
from asset_intelligence.prompt_generator import PromptGenerator
from asset_intelligence.style_system import StyleSystem


@dataclass(slots=True)
class AssetIntelligenceServices:
    """Wired architecture skeleton for Phase 4.7 (no inference)."""

    concept_graph: ConceptGraph
    library: AssetLibrary
    styles: StyleSystem
    planner: AssetPlanner
    prompts: PromptGenerator
    backend: NullImageBackend
    concept_cache: ConceptCache
    asset_cache: AssetCache
    prompt_cache: PromptCache
    style_cache: StyleCache
    generation_cache: GenerationCache


def build_default_services(
    *, styles_dir: Path | None = None
) -> AssetIntelligenceServices:
    """Construct in-memory implementations with constructor injection."""
    library = AssetLibrary()
    styles = StyleSystem(styles_dir=styles_dir)
    return AssetIntelligenceServices(
        concept_graph=ConceptGraph(),
        library=library,
        styles=styles,
        planner=AssetPlanner(library),
        prompts=PromptGenerator(),
        backend=NullImageBackend(),
        concept_cache=ConceptCache(),
        asset_cache=AssetCache(),
        prompt_cache=PromptCache(),
        style_cache=StyleCache(),
        generation_cache=GenerationCache(),
    )
