"""VisualIntelligenceService — single façade over the module.

This is the integration seam for the existing pipeline. Given raw scene data it
returns, per scene, a :class:`VisualIntent`, a :class:`RenderingStrategy`, and a
backward-compatible :class:`LayeredScene`. It performs no rendering and calls no
LLM; it composes the analyzer, router, renderer registry, and (optionally) the
asset repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.visual_intelligence.asset_router import RouterConfig, VisualAssetRouter
from app.services.visual_intelligence.intent_analyzer import VisualIntentAnalyzer
from app.services.visual_intelligence.layers import LayeredScene, LayeredSceneComposer
from app.services.visual_intelligence.renderers.registry import (
    RendererRegistry,
    default_registry,
)
from app.services.visual_intelligence.repository import AssetRepository
from app.services.visual_intelligence.schemas import (
    RenderingStrategy,
    SceneInput,
    VisualIntent,
)


@dataclass
class ScenePlan:
    """Everything the pipeline needs to produce one scene's visual."""

    scene_id: str
    intent: VisualIntent
    strategy: RenderingStrategy
    layered_scene: LayeredScene

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "intent": self.intent.model_dump(mode="json"),
            "strategy": self.strategy.model_dump(mode="json"),
            "layered_scene": self.layered_scene.to_legacy_dict(),
        }


@dataclass
class VisualIntelligenceService:
    """Compose analyzer + router + registry (+ optional repository)."""

    analyzer: VisualIntentAnalyzer = field(default_factory=VisualIntentAnalyzer)
    registry: RendererRegistry = field(default_factory=default_registry)
    router_config: RouterConfig = field(default_factory=RouterConfig)
    repository: AssetRepository | None = None

    def __post_init__(self) -> None:
        self._router = VisualAssetRouter(self.registry, self.router_config)
        self._composer = LayeredSceneComposer()

    @classmethod
    def with_cache(cls, cache_dir: str | Path, **kwargs: Any) -> VisualIntelligenceService:
        return cls(repository=AssetRepository(cache_dir), **kwargs)

    # ---- planning -------------------------------------------------------- #

    def plan_scene(self, scene: SceneInput | dict[str, Any]) -> ScenePlan:
        scene_input = (
            scene if isinstance(scene, SceneInput) else SceneInput.model_validate(scene)
        )
        intent = self.analyzer.analyze(scene_input)
        strategy = self._router.route(intent)
        layered = self._composer.compose(
            strategy, duration_sec=intent.estimated_duration
        )
        return ScenePlan(
            scene_id=scene_input.scene_id,
            intent=intent,
            strategy=strategy,
            layered_scene=layered,
        )

    def plan_scenes(
        self, scenes: list[SceneInput | dict[str, Any]]
    ) -> list[ScenePlan]:
        return [self.plan_scene(s) for s in scenes]

    # ---- discovery ------------------------------------------------------- #

    def describe_renderers(self) -> list[dict[str, object]]:
        return self.registry.describe()
