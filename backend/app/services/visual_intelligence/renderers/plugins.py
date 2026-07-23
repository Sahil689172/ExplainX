"""Concrete renderer plugins — capability declarations only.

Each class declares what it can render, its cost/time baseline, and output
formats. None of them import another plugin. They intentionally contain no
rendering logic (the real engines live in already-completed phases); a backend
is bound at call time via :meth:`RendererPlugin.bind`.
"""

from __future__ import annotations

from app.services.visual_intelligence.renderers.base import (
    RendererCapability,
    RendererPlugin,
)
from app.services.visual_intelligence.schemas import RendererType, VisualType


class MermaidRendererPlugin(RendererPlugin):
    """Text-defined diagrams: flowcharts, graphs, simple timelines."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.MERMAID,
            display_name="Mermaid",
            visual_types=frozenset(
                {VisualType.FLOWCHART, VisualType.DIAGRAM, VisualType.TIMELINE}
            ),
            output_formats=frozenset({"svg", "png"}),
            supports_animation=False,
            quality=0.7,
            base_cost=0.15,
            base_time_sec=1.5,
        )


class SVGRendererPlugin(RendererPlugin):
    """Vector illustrations, tables, labelled diagrams."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.SVG,
            display_name="SVG",
            visual_types=frozenset(
                {
                    VisualType.DIAGRAM,
                    VisualType.TABLE,
                    VisualType.ILLUSTRATION,
                    VisualType.TEXT_ONLY,
                }
            ),
            output_formats=frozenset({"svg", "png"}),
            supports_animation=True,
            quality=0.75,
            base_cost=0.2,
            base_time_sec=2.0,
        )


class MatplotlibRendererPlugin(RendererPlugin):
    """Data-driven charts and plots."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.MATPLOTLIB,
            display_name="Matplotlib",
            visual_types=frozenset({VisualType.CHART, VisualType.TABLE}),
            output_formats=frozenset({"png", "svg"}),
            supports_animation=False,
            quality=0.8,
            base_cost=0.25,
            base_time_sec=2.5,
        )


class ManimRendererPlugin(RendererPlugin):
    """Animated mathematical / scientific explanations."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.MANIM,
            display_name="Manim",
            visual_types=frozenset(
                {VisualType.MATHEMATICAL, VisualType.SCIENTIFIC, VisualType.DIAGRAM}
            ),
            output_formats=frozenset({"png", "mp4"}),
            supports_animation=True,
            quality=0.95,
            base_cost=0.9,
            base_time_sec=12.0,
        )


class OpenVINORendererPlugin(RendererPlugin):
    """Diffusion-generated photos, illustrations, maps, scientific renders."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.OPENVINO,
            display_name="OpenVINO Diffusion",
            visual_types=frozenset(
                {
                    VisualType.PHOTO,
                    VisualType.ILLUSTRATION,
                    VisualType.SCIENTIFIC,
                    VisualType.MAP,
                    VisualType.MIXED,
                }
            ),
            output_formats=frozenset({"png"}),
            supports_animation=False,
            quality=0.85,
            base_cost=1.0,
            base_time_sec=15.0,
        )


class IconRendererPlugin(RendererPlugin):
    """Single-glyph icons and pictograms."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.ICON,
            display_name="Icon",
            visual_types=frozenset({VisualType.ICON}),
            output_formats=frozenset({"svg", "png"}),
            supports_animation=False,
            quality=0.7,
            base_cost=0.05,
            base_time_sec=0.5,
        )


class BackgroundRendererPlugin(RendererPlugin):
    """Full-frame gradient / texture backgrounds."""

    def capability(self) -> RendererCapability:
        return RendererCapability(
            renderer_id=RendererType.BACKGROUND,
            display_name="Background",
            visual_types=frozenset({VisualType.BACKGROUND}),
            output_formats=frozenset({"png"}),
            supports_animation=False,
            quality=0.6,
            base_cost=0.05,
            base_time_sec=0.4,
        )
