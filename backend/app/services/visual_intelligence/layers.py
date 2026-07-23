"""Multi-layer scene composition model (additive, backward compatible).

This extends the *concept* of a composed scene to support independent visual
layers — Background, Foreground, Diagram, Overlay, Labels, Icons, Effects —
each with its own optional animation. It does **not** modify the existing Scene
Composer or the Timeline Engine; it is a parallel, opt-in model.

Backward compatibility:

* :meth:`LayeredScene.from_single_asset` reproduces the legacy single-image
  behaviour (one Background/Foreground layer).
* :meth:`LayeredScene.to_legacy_dict` emits a flat structure the existing
  pipeline can consume, so nothing downstream needs to change.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.visual_intelligence.schemas import (
    LayerType,
    RendererType,
    RenderingStrategy,
)

# Default painter's-order z-index per layer (lower = drawn first / behind).
_LAYER_Z_ORDER: dict[LayerType, int] = {
    LayerType.BACKGROUND: 0,
    LayerType.FOREGROUND: 10,
    LayerType.DIAGRAM: 20,
    LayerType.OVERLAY: 30,
    LayerType.ICONS: 40,
    LayerType.LABELS: 50,
    LayerType.EFFECTS: 60,
}


class LayerAnimation(BaseModel):
    """Independent animation spec for one layer (metadata only).

    These values are advisory metadata consumed by whatever renders/animates a
    layer. They deliberately do not reference the Timeline Engine so that engine
    remains untouched.
    """

    model_config = ConfigDict(extra="forbid")

    kind: str = "none"          # e.g. none | fade | slide | zoom | draw | pulse
    start: float = 0.0          # seconds, relative to scene start
    duration: float = 0.0       # seconds; 0 => whole scene
    easing: str = "ease-in-out"
    params: dict[str, Any] = Field(default_factory=dict)


class VisualLayer(BaseModel):
    """One independently-animatable layer within a scene."""

    model_config = ConfigDict(extra="forbid")

    layer_type: LayerType
    z_index: int
    renderer: RendererType | None = None
    asset_path: str | None = None
    asset_hash: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    visible: bool = True
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    animation: LayerAnimation = Field(default_factory=LayerAnimation)


class LayeredScene(BaseModel):
    """A scene composed of ordered, independently-animated visual layers."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    duration_sec: float = 0.0
    layers: list[VisualLayer] = Field(default_factory=list)

    def ordered(self) -> list[VisualLayer]:
        """Layers sorted back-to-front for compositing."""
        return sorted(self.layers, key=lambda layer_item: layer_item.z_index)

    def layer(self, layer_type: LayerType) -> VisualLayer | None:
        for layer_item in self.layers:
            if layer_item.layer_type == layer_type:
                return layer_item
        return None

    # ---- backward compatibility ----------------------------------------- #

    @classmethod
    def from_single_asset(
        cls,
        scene_id: str,
        *,
        asset_path: str,
        duration_sec: float = 0.0,
        as_background: bool = True,
    ) -> LayeredScene:
        """Legacy single-image scene → one-layer LayeredScene."""
        layer_type = LayerType.BACKGROUND if as_background else LayerType.FOREGROUND
        return cls(
            scene_id=scene_id,
            duration_sec=duration_sec,
            layers=[
                VisualLayer(
                    layer_type=layer_type,
                    z_index=_LAYER_Z_ORDER[layer_type],
                    asset_path=asset_path,
                )
            ],
        )

    def to_legacy_dict(self) -> dict[str, Any]:
        """Flatten to the structure the existing pipeline already understands.

        The first Background/Foreground layer becomes ``illustration_path`` so
        downstream code that expects a single image keeps working.
        """
        ordered = self.ordered()
        primary = next(
            (
                layer_item
                for layer_item in ordered
                if layer_item.layer_type in (LayerType.BACKGROUND, LayerType.FOREGROUND)
                and layer_item.asset_path
            ),
            None,
        )
        illustration = primary.asset_path if primary else (
            ordered[0].asset_path if ordered and ordered[0].asset_path else None
        )
        return {
            "scene_id": self.scene_id,
            "duration": self.duration_sec,
            "illustration_path": illustration,
            "layers": [
                {
                    "type": layer_item.layer_type.value,
                    "z_index": layer_item.z_index,
                    "renderer": layer_item.renderer.value if layer_item.renderer else None,
                    "asset_path": layer_item.asset_path,
                    "opacity": layer_item.opacity,
                    "visible": layer_item.visible,
                    "animation": layer_item.animation.model_dump(),
                }
                for layer_item in ordered
            ],
        }


class LayeredSceneComposer:
    """Build a :class:`LayeredScene` from a routing strategy.

    Additive: it consumes the router's output and produces a layer stack. It
    never renders and never touches the existing composer or timeline.
    """

    def compose(
        self,
        strategy: RenderingStrategy,
        *,
        duration_sec: float = 0.0,
        assets: dict[LayerType, str] | None = None,
        animations: dict[LayerType, LayerAnimation] | None = None,
    ) -> LayeredScene:
        assets = assets or {}
        animations = animations or {}

        layers: list[VisualLayer] = []
        for layer_type in strategy.layers:
            z = _LAYER_Z_ORDER.get(layer_type, 100)
            # The strategy's primary renderer owns the content layer; other
            # layers default to no explicit renderer (filled by the pipeline).
            renderer: RendererType | None = None
            if layer_type in (LayerType.DIAGRAM, LayerType.FOREGROUND):
                renderer = strategy.primary_renderer
            layers.append(
                VisualLayer(
                    layer_type=layer_type,
                    z_index=z,
                    renderer=renderer,
                    asset_path=assets.get(layer_type),
                    animation=animations.get(layer_type, LayerAnimation()),
                )
            )
        return LayeredScene(
            scene_id=strategy.scene_id, duration_sec=duration_sec, layers=layers
        )
