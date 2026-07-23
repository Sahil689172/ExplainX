"""Unit tests for multi-layer composition and the service façade."""

from __future__ import annotations

from app.services.visual_intelligence import (
    SceneInput,
    VisualIntelligenceService,
)
from app.services.visual_intelligence.layers import (
    LayerAnimation,
    LayeredScene,
    LayeredSceneComposer,
)
from app.services.visual_intelligence.schemas import (
    Complexity,
    LayerType,
    RendererType,
    RenderingStrategy,
    VisualType,
)


def _strategy(layers) -> RenderingStrategy:
    return RenderingStrategy(
        scene_id="s1",
        visual_type=VisualType.DIAGRAM,
        primary_renderer=RendererType.SVG,
        layers=layers,
    )


def test_layered_scene_ordering():
    composer = LayeredSceneComposer()
    scene = composer.compose(
        _strategy([LayerType.LABELS, LayerType.BACKGROUND, LayerType.DIAGRAM]),
        duration_sec=8.0,
    )
    ordered = scene.ordered()
    # Background must come first, labels last.
    assert ordered[0].layer_type == LayerType.BACKGROUND
    assert ordered[-1].layer_type == LayerType.LABELS


def test_layer_gets_primary_renderer_for_content_layers():
    composer = LayeredSceneComposer()
    scene = composer.compose(_strategy([LayerType.BACKGROUND, LayerType.DIAGRAM]))
    diagram = scene.layer(LayerType.DIAGRAM)
    assert diagram is not None
    assert diagram.renderer == RendererType.SVG


def test_independent_layer_animation():
    composer = LayeredSceneComposer()
    scene = composer.compose(
        _strategy([LayerType.BACKGROUND, LayerType.DIAGRAM]),
        animations={LayerType.DIAGRAM: LayerAnimation(kind="draw", duration=3.0)},
    )
    diagram = scene.layer(LayerType.DIAGRAM)
    assert diagram.animation.kind == "draw"
    assert diagram.animation.duration == 3.0
    # Background keeps its own default animation, independent of diagram.
    assert scene.layer(LayerType.BACKGROUND).animation.kind == "none"


def test_backward_compat_from_single_asset():
    scene = LayeredScene.from_single_asset("s1", asset_path="/imgs/earth.png", duration_sec=6.0)
    assert len(scene.layers) == 1
    legacy = scene.to_legacy_dict()
    assert legacy["illustration_path"] == "/imgs/earth.png"
    assert legacy["duration"] == 6.0


def test_to_legacy_dict_exposes_illustration_path():
    composer = LayeredSceneComposer()
    scene = composer.compose(
        _strategy([LayerType.BACKGROUND, LayerType.DIAGRAM]),
        assets={LayerType.BACKGROUND: "/imgs/bg.png"},
    )
    legacy = scene.to_legacy_dict()
    assert legacy["illustration_path"] == "/imgs/bg.png"
    assert isinstance(legacy["layers"], list)


def test_service_plan_scene_end_to_end():
    service = VisualIntelligenceService()
    plan = service.plan_scene(
        SceneInput(
            scene_id="scene_01",
            title="The Water Cycle",
            narration="Water evaporates then condenses in a repeating process step by step.",
            keywords=["process", "cycle"],
            educational_concepts=["evaporation", "condensation"],
            learning_objective="Explain the stages of the water cycle",
        )
    )
    assert plan.scene_id == "scene_01"
    assert plan.intent.visual_type == VisualType.FLOWCHART
    assert plan.strategy.primary_renderer == RendererType.MERMAID
    assert plan.layered_scene.layers
    d = plan.to_dict()
    assert d["intent"]["visual_type"] == "flowchart"
    assert "layered_scene" in d


def test_service_accepts_dict_input():
    service = VisualIntelligenceService()
    plan = service.plan_scene({"scene_id": "x", "narration": "a bar chart of data percentages"})
    assert plan.intent.visual_type == VisualType.CHART


def test_service_describe_renderers():
    service = VisualIntelligenceService()
    described = service.describe_renderers()
    assert len(described) == 7
    assert all("renderer_id" in d for d in described)


def test_service_plan_many():
    service = VisualIntelligenceService()
    plans = service.plan_scenes(
        [
            {"scene_id": "a", "narration": "timeline of history over time"},
            {"scene_id": "b", "narration": "equation proof theorem geometry"},
        ]
    )
    assert plans[0].intent.visual_type == VisualType.TIMELINE
    assert plans[1].intent.visual_type == VisualType.MATHEMATICAL
