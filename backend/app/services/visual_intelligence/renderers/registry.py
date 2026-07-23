"""Renderer plugin registry — plugin discovery without cross-plugin coupling."""

from __future__ import annotations

from app.services.visual_intelligence.renderers.base import RendererPlugin
from app.services.visual_intelligence.renderers.plugins import (
    BackgroundRendererPlugin,
    IconRendererPlugin,
    ManimRendererPlugin,
    MatplotlibRendererPlugin,
    MermaidRendererPlugin,
    OpenVINORendererPlugin,
    SVGRendererPlugin,
)
from app.services.visual_intelligence.schemas import (
    RendererType,
    VisualIntent,
    VisualType,
)


class RendererRegistry:
    """Holds renderer plugins and answers capability queries.

    The registry is the only component aware of the full plugin set; individual
    plugins remain isolated. New renderers are added with :meth:`register`,
    making the architecture plugin-based and open for extension.
    """

    def __init__(self) -> None:
        self._plugins: dict[RendererType, RendererPlugin] = {}

    def register(self, plugin: RendererPlugin, *, replace: bool = False) -> None:
        rid = plugin.capability().renderer_id
        if rid in self._plugins and not replace:
            raise ValueError(f"Renderer already registered: {rid.value}")
        self._plugins[rid] = plugin

    def unregister(self, renderer_id: RendererType) -> None:
        self._plugins.pop(renderer_id, None)

    def get(self, renderer_id: RendererType) -> RendererPlugin | None:
        return self._plugins.get(renderer_id)

    def __contains__(self, renderer_id: RendererType) -> bool:
        return renderer_id in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)

    def all(self) -> list[RendererPlugin]:
        return list(self._plugins.values())

    def renderers_for(self, visual_type: VisualType) -> list[RendererType]:
        """Every registered renderer that can produce ``visual_type``."""
        return [
            rid
            for rid, plugin in self._plugins.items()
            if visual_type in plugin.capability().visual_types
        ]

    def candidates(self, intent: VisualIntent) -> list[RendererPlugin]:
        """Plugins that support ``intent``, best (cheapest capable) first."""
        supporting = [p for p in self._plugins.values() if p.supports(intent)]
        supporting.sort(key=lambda p: (p.estimate_cost(intent), -p.capability().quality))
        return supporting

    def describe(self) -> list[dict[str, object]]:
        return [p.metadata() for p in self._plugins.values()]


def default_registry() -> RendererRegistry:
    """Registry pre-loaded with the seven standard renderer plugins."""
    registry = RendererRegistry()
    for plugin in (
        MermaidRendererPlugin(),
        SVGRendererPlugin(),
        MatplotlibRendererPlugin(),
        ManimRendererPlugin(),
        OpenVINORendererPlugin(),
        IconRendererPlugin(),
        BackgroundRendererPlugin(),
    ):
        registry.register(plugin)
    return registry
