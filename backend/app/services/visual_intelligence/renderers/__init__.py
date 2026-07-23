"""Plugin-based renderer interfaces for Visual Intelligence.

Each renderer is an isolated plugin implementing :class:`RendererPlugin`. No
plugin imports or references another plugin — capabilities are declared through
``supports()`` and discovered via :class:`RendererRegistry`. These plugins do
**not** modify or replace the existing rendering engines; they describe
capabilities, cost, and time so the router can choose, and expose a uniform
``render()`` seam that a caller binds to a real backend later.
"""

from __future__ import annotations

from app.services.visual_intelligence.renderers.base import (
    RendererCapability,
    RendererPlugin,
    RenderOutcome,
)
from app.services.visual_intelligence.renderers.plugins import (
    BackgroundRendererPlugin,
    IconRendererPlugin,
    ManimRendererPlugin,
    MatplotlibRendererPlugin,
    MermaidRendererPlugin,
    OpenVINORendererPlugin,
    SVGRendererPlugin,
)
from app.services.visual_intelligence.renderers.registry import (
    RendererRegistry,
    default_registry,
)

__all__ = [
    "BackgroundRendererPlugin",
    "IconRendererPlugin",
    "ManimRendererPlugin",
    "MatplotlibRendererPlugin",
    "MermaidRendererPlugin",
    "OpenVINORendererPlugin",
    "RendererCapability",
    "RendererPlugin",
    "RendererRegistry",
    "RenderOutcome",
    "SVGRendererPlugin",
    "default_registry",
]
