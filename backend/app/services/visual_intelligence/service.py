"""VisualIntelligenceService — single façade over the module.

This is the integration seam for the existing pipeline. Given raw scene data it
returns, per scene, a :class:`VisualIntent`, a :class:`RenderingStrategy`, and a
backward-compatible :class:`LayeredScene`. It performs no rendering and calls no
LLM; it composes the analyzer, router, renderer registry, and (optionally) the
asset repository.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.visual_intelligence.asset_router import RouterConfig, VisualAssetRouter
from app.services.visual_intelligence.cache import compute_hash
from app.services.visual_intelligence.intent_analyzer import VisualIntentAnalyzer
from app.services.visual_intelligence.layers import LayeredScene, LayeredSceneComposer
from app.services.visual_intelligence.renderers.registry import (
    RendererRegistry,
    default_registry,
)
from app.services.visual_intelligence.repository import AssetRepository
from app.services.visual_intelligence.schemas import (
    RenderingStrategy,
    RenderRequest,
    SceneInput,
    VisualIntent,
)

# Stdlib logger (no hard app coupling → preserves dependency inversion). The
# app's root logging config picks these records up automatically.
logger = logging.getLogger("explainx.visual_intelligence")


def prospective_cache_key(
    scene: SceneInput, intent: VisualIntent, strategy: RenderingStrategy
) -> str:
    """SHA256 the asset this plan *would* request (no generation performed).

    Lets callers log/inspect the cache key up front and later reuse it when an
    asset is actually produced by the (separate) rendering engine.
    """
    request = RenderRequest(
        prompt=(scene.title or scene.narration or scene.scene_id).strip(),
        model="",
        renderer=strategy.primary_renderer,
        seed=None,
        parameters={**strategy.renderer_options, "visual_type": intent.visual_type.value},
    )
    return compute_hash(request)


@dataclass
class ScenePlan:
    """Everything the pipeline needs to produce one scene's visual."""

    scene_id: str
    intent: VisualIntent
    strategy: RenderingStrategy
    layered_scene: LayeredScene
    cache_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "intent": self.intent.model_dump(mode="json"),
            "strategy": self.strategy.model_dump(mode="json"),
            "layered_scene": self.layered_scene.to_legacy_dict(),
            "cache_key": self.cache_key,
        }

    def to_timeline_scene(self) -> dict[str, Any]:
        """Adapt this plan to the Timeline Engine's scene-JSON interface."""
        from app.services.visual_intelligence.timeline_adapter import (
            scene_plan_to_timeline_scene,
        )

        return scene_plan_to_timeline_scene(self)


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

    def analyze(self, scene: SceneInput | dict[str, Any]) -> VisualIntent:
        """Classify a scene's visual intent only (no routing / composition)."""
        scene_input = (
            scene if isinstance(scene, SceneInput) else SceneInput.model_validate(scene)
        )
        return self.analyzer.analyze(scene_input)

    def plan_scene(self, scene: SceneInput | dict[str, Any]) -> ScenePlan:
        scene_input = (
            scene if isinstance(scene, SceneInput) else SceneInput.model_validate(scene)
        )
        intent = self.analyzer.analyze(scene_input)
        strategy = self._router.route(intent)
        layered = self._composer.compose(
            strategy, duration_sec=intent.estimated_duration
        )
        cache_key = prospective_cache_key(scene_input, intent, strategy)

        logger.debug(
            "visual plan: scene=%s intent=%s renderer=%s complexity=%s "
            "est_duration=%.2fs cache_key=%s",
            scene_input.scene_id,
            intent.visual_type.value,
            strategy.primary_renderer.value,
            intent.complexity.value,
            intent.estimated_duration,
            cache_key[:16],
            extra={
                "event": "visual_intelligence_plan",
                "component": "visual_intelligence",
                "scene_id": scene_input.scene_id,
                "visual_intent": intent.visual_type.value,
                "selected_renderer": strategy.primary_renderer.value,
                "fallback_renderers": [r.value for r in strategy.fallback_renderers],
                "complexity": intent.complexity.value,
                "confidence": intent.confidence,
                "estimated_duration_sec": intent.estimated_duration,
                "cache_key": cache_key,
            },
        )

        return ScenePlan(
            scene_id=scene_input.scene_id,
            intent=intent,
            strategy=strategy,
            layered_scene=layered,
            cache_key=cache_key,
        )

    def plan_scenes(
        self, scenes: list[SceneInput | dict[str, Any]]
    ) -> list[ScenePlan]:
        return [self.plan_scene(s) for s in scenes]

    def plan_script(self, script: Any) -> list[ScenePlan]:
        """Plan visuals for an entire EducationalScript (model or dict).

        This is the single entry point the orchestration layer calls right
        after ``EducationalScript`` generation. Uses the pipeline adapter to map
        teaching sections → :class:`SceneInput` without importing any completed
        phase (duck typing).
        """
        from app.services.visual_intelligence.pipeline_adapter import (
            script_to_scene_inputs,
        )

        return self.plan_scenes(script_to_scene_inputs(script))

    def plan_script_to_timeline(self, script: Any) -> list[dict[str, Any]]:
        """Plan a whole script and adapt every plan to Timeline scene JSON."""
        from app.services.visual_intelligence.timeline_adapter import (
            scene_plans_to_timeline_scenes,
        )

        return scene_plans_to_timeline_scenes(self.plan_script(script))

    # ---- discovery ------------------------------------------------------- #

    def describe_renderers(self) -> list[dict[str, object]]:
        return self.registry.describe()
