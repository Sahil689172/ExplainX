"""Renderer plugin contract.

Every renderer plugin implements the same five-method interface:

* ``supports(intent)``     — can this plugin produce the requested visual?
* ``render(request)``      — uniform seam to produce an asset (binding-based).
* ``estimate_cost(intent)``— relative production cost (unitless, 0..1+).
* ``estimate_time(intent)``— wall-clock seconds estimate.
* ``metadata()``           — static descriptor (id, type, formats, quality).

Plugins are deliberately ignorant of one another. They declare which
:class:`~app.services.visual_intelligence.schemas.VisualType` values they can
handle; the registry and router use that to select without any plugin knowing
about the others.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from app.services.visual_intelligence.schemas import (
    RendererType,
    RenderRequest,
    VisualIntent,
    VisualType,
)


@dataclass(frozen=True, slots=True)
class RendererCapability:
    """Static description of a renderer plugin."""

    renderer_id: RendererType
    display_name: str
    visual_types: frozenset[VisualType]
    output_formats: frozenset[str]        # e.g. {"png", "svg"}
    supports_animation: bool
    quality: float                        # 0..1 relative output quality
    base_cost: float                      # 0..1+ relative cost
    base_time_sec: float                  # baseline wall-clock estimate


@dataclass(slots=True)
class RenderOutcome:
    """Result of binding + invoking a plugin's render seam."""

    renderer_id: RendererType
    asset_path: str | None
    generated: bool
    detail: str = ""
    extra: dict[str, object] = field(default_factory=dict)


# A render backend is any callable the caller binds to actually produce pixels.
RenderBackend = Callable[[RenderRequest], RenderOutcome]


class RendererPlugin(ABC):
    """Uniform, self-contained renderer plugin interface."""

    def __init__(self, backend: RenderBackend | None = None) -> None:
        # The plugin never generates on its own; a caller may bind a backend.
        self._backend = backend

    # ---- capability ------------------------------------------------------ #

    @abstractmethod
    def capability(self) -> RendererCapability:
        """Return this plugin's static capability descriptor."""

    def metadata(self) -> dict[str, object]:
        """Serializable static descriptor for discovery / documentation."""
        cap = self.capability()
        return {
            "renderer_id": cap.renderer_id.value,
            "display_name": cap.display_name,
            "visual_types": sorted(v.value for v in cap.visual_types),
            "output_formats": sorted(cap.output_formats),
            "supports_animation": cap.supports_animation,
            "quality": cap.quality,
            "base_cost": cap.base_cost,
            "base_time_sec": cap.base_time_sec,
        }

    # ---- selection ------------------------------------------------------- #

    def supports(self, intent: VisualIntent) -> bool:
        """True when this plugin can produce the intent's visual type."""
        return intent.visual_type in self.capability().visual_types

    def estimate_cost(self, intent: VisualIntent) -> float:
        """Relative cost, scaled by scene complexity."""
        from app.services.visual_intelligence.schemas import Complexity

        multiplier = {
            Complexity.TRIVIAL: 0.5,
            Complexity.SIMPLE: 1.0,
            Complexity.MODERATE: 1.6,
            Complexity.COMPLEX: 2.5,
        }[intent.complexity]
        return round(self.capability().base_cost * multiplier, 4)

    def estimate_time(self, intent: VisualIntent) -> float:
        """Wall-clock seconds estimate, scaled by scene complexity."""
        from app.services.visual_intelligence.schemas import Complexity

        multiplier = {
            Complexity.TRIVIAL: 0.5,
            Complexity.SIMPLE: 1.0,
            Complexity.MODERATE: 1.8,
            Complexity.COMPLEX: 3.0,
        }[intent.complexity]
        return round(self.capability().base_time_sec * multiplier, 3)

    # ---- production seam ------------------------------------------------- #

    def bind(self, backend: RenderBackend) -> None:
        """Attach a real rendering backend without the plugin knowing details."""
        self._backend = backend

    def render(self, request: RenderRequest) -> RenderOutcome:
        """Produce an asset via the bound backend.

        The plugin itself never generates pixels; if no backend is bound it
        returns a non-generated outcome so callers can decide what to do. This
        keeps the existing rendering engine untouched.
        """
        cap = self.capability()
        if self._backend is None:
            return RenderOutcome(
                renderer_id=cap.renderer_id,
                asset_path=None,
                generated=False,
                detail="no backend bound — plugin describes capability only",
            )
        return self._backend(request)
