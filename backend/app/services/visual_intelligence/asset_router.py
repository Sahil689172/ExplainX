"""VisualAssetRouter — map a VisualIntent to a RenderingStrategy.

The router decides *which* renderer should produce a visual and with what
options and fallbacks. It **never generates assets** — it only plans. Routing
is fully configurable via :class:`RouterConfig` (per-visual-type overrides,
renderer preference order, forced fallbacks, and default layers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.visual_intelligence.renderers.registry import (
    RendererRegistry,
    default_registry,
)
from app.services.visual_intelligence.schemas import (
    LayerType,
    RendererType,
    RenderingStrategy,
    VisualIntent,
    VisualType,
)


@dataclass
class RouterConfig:
    """Fully configurable routing policy.

    Attributes
    ----------
    overrides:
        Force a specific renderer for a visual type, bypassing scoring.
    preference_order:
        Global tiebreaker order; renderers earlier in the list win when costs
        are equal.
    renderer_options:
        Per-renderer keyword options injected into the strategy.
    default_layers:
        Layers attached per visual type (used by the layered composer).
    max_fallbacks:
        Maximum number of fallback renderers to include.
    """

    overrides: dict[VisualType, RendererType] = field(default_factory=dict)
    preference_order: list[RendererType] = field(
        default_factory=lambda: [
            RendererType.MERMAID,
            RendererType.SVG,
            RendererType.MATPLOTLIB,
            RendererType.ICON,
            RendererType.BACKGROUND,
            RendererType.MANIM,
            RendererType.OPENVINO,
        ]
    )
    renderer_options: dict[RendererType, dict[str, Any]] = field(default_factory=dict)
    default_layers: dict[VisualType, list[LayerType]] = field(default_factory=dict)
    max_fallbacks: int = 2

    def preference_rank(self, renderer: RendererType) -> int:
        try:
            return self.preference_order.index(renderer)
        except ValueError:
            return len(self.preference_order)


_DEFAULT_LAYERS: dict[VisualType, list[LayerType]] = {
    VisualType.DIAGRAM: [LayerType.BACKGROUND, LayerType.DIAGRAM, LayerType.LABELS],
    VisualType.FLOWCHART: [LayerType.BACKGROUND, LayerType.DIAGRAM, LayerType.LABELS],
    VisualType.TIMELINE: [LayerType.BACKGROUND, LayerType.DIAGRAM, LayerType.LABELS],
    VisualType.CHART: [LayerType.BACKGROUND, LayerType.FOREGROUND, LayerType.LABELS],
    VisualType.TABLE: [LayerType.BACKGROUND, LayerType.FOREGROUND, LayerType.LABELS],
    VisualType.MAP: [LayerType.BACKGROUND, LayerType.FOREGROUND, LayerType.OVERLAY],
    VisualType.MATHEMATICAL: [LayerType.BACKGROUND, LayerType.DIAGRAM, LayerType.EFFECTS],
    VisualType.SCIENTIFIC: [LayerType.BACKGROUND, LayerType.FOREGROUND, LayerType.LABELS],
    VisualType.ILLUSTRATION: [LayerType.BACKGROUND, LayerType.FOREGROUND],
    VisualType.PHOTO: [LayerType.BACKGROUND, LayerType.FOREGROUND],
    VisualType.ICON: [LayerType.ICONS],
    VisualType.BACKGROUND: [LayerType.BACKGROUND],
    VisualType.TEXT_ONLY: [LayerType.BACKGROUND, LayerType.LABELS],
    VisualType.MIXED: [
        LayerType.BACKGROUND,
        LayerType.FOREGROUND,
        LayerType.DIAGRAM,
        LayerType.OVERLAY,
        LayerType.LABELS,
    ],
}


class VisualAssetRouter:
    """Plan a :class:`RenderingStrategy` for a :class:`VisualIntent`."""

    def __init__(
        self,
        registry: RendererRegistry | None = None,
        config: RouterConfig | None = None,
    ) -> None:
        self._registry = registry or default_registry()
        self._config = config or RouterConfig()

    @property
    def config(self) -> RouterConfig:
        return self._config

    def route(self, intent: VisualIntent) -> RenderingStrategy:
        primary, fallbacks, reasoning = self._select_renderers(intent)

        primary_plugin = self._registry.get(primary)
        est_cost = primary_plugin.estimate_cost(intent) if primary_plugin else 0.0
        est_time = primary_plugin.estimate_time(intent) if primary_plugin else 0.0

        options = dict(self._config.renderer_options.get(primary, {}))
        layers = self._config.default_layers.get(
            intent.visual_type, _DEFAULT_LAYERS.get(intent.visual_type, [])
        )

        return RenderingStrategy(
            scene_id=intent.scene_id,
            visual_type=intent.visual_type,
            primary_renderer=primary,
            fallback_renderers=fallbacks,
            renderer_options=options,
            layers=list(layers),
            reasoning=reasoning,
            estimated_cost=est_cost,
            estimated_time_sec=est_time,
        )

    def route_many(self, intents: list[VisualIntent]) -> list[RenderingStrategy]:
        return [self.route(i) for i in intents]

    # ---- selection ------------------------------------------------------- #

    def _select_renderers(
        self, intent: VisualIntent
    ) -> tuple[RendererType, list[RendererType], str]:
        # 1) Explicit override always wins.
        override = self._config.overrides.get(intent.visual_type)
        if override is not None and override in self._registry:
            fallbacks = self._fallbacks(intent, exclude={override})
            return override, fallbacks, f"Config override → {override.value}."

        # 2) Capability-driven candidates from the registry.
        candidates = self._registry.candidates(intent)
        if candidates:
            ranked = sorted(
                candidates,
                key=lambda p: (
                    p.estimate_cost(intent),
                    self._config.preference_rank(p.capability().renderer_id),
                    -p.capability().quality,
                ),
            )
            ids = [p.capability().renderer_id for p in ranked]

            # Honour the analyzer's suggestion if it is a valid candidate.
            if intent.suggested_renderer in ids:
                primary = intent.suggested_renderer
                reasoning = (
                    f"Analyzer suggested {primary.value}; confirmed as capable "
                    f"for {intent.visual_type.value}."
                )
            else:
                primary = ids[0]
                reasoning = (
                    f"Selected cheapest capable renderer {primary.value} for "
                    f"{intent.visual_type.value}."
                )
            fallbacks = [rid for rid in ids if rid != primary][: self._config.max_fallbacks]
            return primary, fallbacks, reasoning

        # 3) Nothing registered can render this — fall back to the suggestion.
        return (
            intent.suggested_renderer,
            [],
            f"No registered renderer supports {intent.visual_type.value}; "
            f"using analyzer suggestion {intent.suggested_renderer.value}.",
        )

    def _fallbacks(
        self, intent: VisualIntent, *, exclude: set[RendererType]
    ) -> list[RendererType]:
        ids = [
            p.capability().renderer_id
            for p in self._registry.candidates(intent)
            if p.capability().renderer_id not in exclude
        ]
        return ids[: self._config.max_fallbacks]
