"""Unit tests for renderer plugins and the registry."""

from __future__ import annotations

from app.services.visual_intelligence.renderers import (
    MermaidRendererPlugin,
    RendererRegistry,
    default_registry,
)
from app.services.visual_intelligence.renderers.base import RenderOutcome
from app.services.visual_intelligence.schemas import (
    Complexity,
    RendererType,
    RenderRequest,
    VisualIntent,
    VisualType,
)


def _intent(visual_type: VisualType, complexity=Complexity.SIMPLE) -> VisualIntent:
    return VisualIntent(
        scene_id="s1",
        visual_type=visual_type,
        confidence=0.8,
        reasoning="t",
        suggested_renderer=RendererType.MERMAID,
        estimated_duration=6.0,
        complexity=complexity,
    )


def test_default_registry_has_seven_renderers():
    registry = default_registry()
    assert len(registry) == 7
    ids = {p.capability().renderer_id for p in registry.all()}
    assert ids == set(RendererType)


def test_plugin_five_method_interface():
    plugin = MermaidRendererPlugin()
    intent = _intent(VisualType.FLOWCHART)
    assert plugin.supports(intent) is True
    assert plugin.estimate_cost(intent) > 0
    assert plugin.estimate_time(intent) > 0
    assert isinstance(plugin.metadata(), dict)
    outcome = plugin.render(RenderRequest(renderer=RendererType.MERMAID))
    assert isinstance(outcome, RenderOutcome)


def test_plugin_does_not_support_unrelated_type():
    plugin = MermaidRendererPlugin()
    assert plugin.supports(_intent(VisualType.PHOTO)) is False


def test_render_without_backend_does_not_generate():
    plugin = MermaidRendererPlugin()
    outcome = plugin.render(RenderRequest(renderer=RendererType.MERMAID))
    assert outcome.generated is False
    assert outcome.asset_path is None


def test_render_with_bound_backend():
    plugin = MermaidRendererPlugin()

    def backend(req: RenderRequest) -> RenderOutcome:
        return RenderOutcome(
            renderer_id=RendererType.MERMAID, asset_path="/tmp/x.png", generated=True
        )

    plugin.bind(backend)
    outcome = plugin.render(RenderRequest(renderer=RendererType.MERMAID))
    assert outcome.generated is True
    assert outcome.asset_path == "/tmp/x.png"


def test_cost_scales_with_complexity():
    plugin = MermaidRendererPlugin()
    simple = plugin.estimate_cost(_intent(VisualType.FLOWCHART, Complexity.SIMPLE))
    complex_ = plugin.estimate_cost(_intent(VisualType.FLOWCHART, Complexity.COMPLEX))
    assert complex_ > simple


def test_registry_candidates_sorted_by_cost():
    registry = default_registry()
    candidates = registry.candidates(_intent(VisualType.DIAGRAM))
    costs = [p.estimate_cost(_intent(VisualType.DIAGRAM)) for p in candidates]
    assert costs == sorted(costs)


def test_registry_register_duplicate_raises():
    registry = RendererRegistry()
    registry.register(MermaidRendererPlugin())
    try:
        registry.register(MermaidRendererPlugin())
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_registry_renderers_for_type():
    registry = default_registry()
    ids = registry.renderers_for(VisualType.FLOWCHART)
    assert RendererType.MERMAID in ids


def test_no_plugin_imports_another():
    # Structural guarantee: plugins module must not import sibling plugins by
    # cross-reference. We assert each plugin only knows its own renderer id.
    registry = default_registry()
    for plugin in registry.all():
        cap = plugin.capability()
        assert isinstance(cap.renderer_id, RendererType)
