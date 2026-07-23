"""Unit tests for VisualAssetRouter and RouterConfig."""

from __future__ import annotations

from app.services.visual_intelligence.asset_router import RouterConfig, VisualAssetRouter
from app.services.visual_intelligence.renderers.registry import default_registry
from app.services.visual_intelligence.schemas import (
    Complexity,
    RendererType,
    VisualIntent,
    VisualType,
)


def _intent(visual_type: VisualType, renderer: RendererType, **kwargs) -> VisualIntent:
    base = dict(
        scene_id="s1",
        visual_type=visual_type,
        confidence=0.8,
        reasoning="test",
        suggested_renderer=renderer,
        estimated_duration=6.0,
        complexity=Complexity.SIMPLE,
    )
    base.update(kwargs)
    return VisualIntent(**base)


def test_router_never_returns_none_primary():
    router = VisualAssetRouter()
    strategy = router.route(_intent(VisualType.FLOWCHART, RendererType.MERMAID))
    assert strategy.primary_renderer is not None
    assert strategy.scene_id == "s1"


def test_router_honours_analyzer_suggestion_when_capable():
    router = VisualAssetRouter()
    strategy = router.route(_intent(VisualType.MATHEMATICAL, RendererType.MANIM))
    assert strategy.primary_renderer == RendererType.MANIM


def test_router_override_wins():
    config = RouterConfig(overrides={VisualType.DIAGRAM: RendererType.MERMAID})
    router = VisualAssetRouter(config=config)
    strategy = router.route(_intent(VisualType.DIAGRAM, RendererType.SVG))
    assert strategy.primary_renderer == RendererType.MERMAID
    assert "override" in strategy.reasoning.lower()


def test_router_provides_fallbacks():
    router = VisualAssetRouter()
    # DIAGRAM is supported by mermaid, svg, manim → expect fallbacks
    strategy = router.route(_intent(VisualType.DIAGRAM, RendererType.SVG))
    assert strategy.primary_renderer == RendererType.SVG
    assert strategy.fallback_renderers
    assert strategy.primary_renderer not in strategy.fallback_renderers


def test_router_populates_layers_and_estimates():
    router = VisualAssetRouter()
    strategy = router.route(_intent(VisualType.CHART, RendererType.MATPLOTLIB))
    assert strategy.layers  # default layers assigned
    assert strategy.estimated_time_sec > 0
    assert strategy.estimated_cost > 0


def test_router_options_injected():
    config = RouterConfig(renderer_options={RendererType.MERMAID: {"theme": "dark"}})
    router = VisualAssetRouter(config=config)
    strategy = router.route(_intent(VisualType.FLOWCHART, RendererType.MERMAID))
    assert strategy.renderer_options.get("theme") == "dark"


def test_router_max_fallbacks_respected():
    config = RouterConfig(max_fallbacks=1)
    router = VisualAssetRouter(config=config)
    strategy = router.route(_intent(VisualType.DIAGRAM, RendererType.SVG))
    assert len(strategy.fallback_renderers) <= 1


def test_router_never_generates_assets():
    # The router has no render method and touches no files.
    router = VisualAssetRouter()
    assert not hasattr(router, "render")
    assert not hasattr(router, "generate")


def test_unregistered_type_uses_suggestion():
    # Empty registry → router falls back to the analyzer suggestion.
    registry = default_registry()
    for rid in list(RendererType):
        registry.unregister(rid)
    router = VisualAssetRouter(registry=registry)
    strategy = router.route(_intent(VisualType.PHOTO, RendererType.OPENVINO))
    assert strategy.primary_renderer == RendererType.OPENVINO
    assert strategy.fallback_renderers == []
