"""Layer collection from scene JSON at a point in time."""

from __future__ import annotations

from typing import Any

from video_renderer.renderer_config import (
    DEFAULT_FOOTER,
    TOPIC_BULLETS,
    TOPIC_SUBTITLES,
    Z_INDEX,
    RendererConfig,
)
from video_renderer.renderer_types import LayerType, RenderLayer, TransformState
from video_renderer.transform_engine import TransformEngine


class LayerManager:
    """Collect visible layers from scene JSON and apply timeline transforms."""

    def __init__(
        self,
        *,
        config: RendererConfig | None = None,
        transform_engine: TransformEngine | None = None,
    ) -> None:
        self._config = config or RendererConfig()
        self._transforms = transform_engine or TransformEngine()

    def collect(
        self,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        current_time: float,
    ) -> list[RenderLayer]:
        keyframes = timeline.get("keyframes") or []
        elements = (scene.get("timeline") or {}).get("elements") or []
        visibility = self._visibility_map(elements, current_time)

        layers: list[RenderLayer] = []
        layers.append(self._background_layer())

        title = str(scene.get("title", "Untitled"))
        topic_key = title.lower()
        layers.append(
            self._text_layer(
                "title",
                LayerType.TITLE,
                title,
                bounds=(self._config.margin, self._config.margin, 800, 44),
                keyframes=keyframes,
                time_s=current_time,
                visible=True,
                z=Z_INDEX["title"],
            )
        )

        subtitle = TOPIC_SUBTITLES.get(topic_key, scene.get("subject", ""))
        if subtitle:
            layers.append(
                self._text_layer(
                    "subtitle",
                    LayerType.SUBTITLE,
                    subtitle,
                    bounds=(self._config.margin, self._config.margin + 48, 800, 28),
                    keyframes=keyframes,
                    time_s=current_time,
                    visible=visibility.get("subtitle", current_time >= 0.2),
                    z=Z_INDEX["subtitle"],
                )
            )

        for asset in scene.get("assets") or []:
            layer = self._asset_layer(asset, keyframes, current_time, visibility)
            if layer:
                layers.append(layer)

        bullets = scene.get("bullets") or TOPIC_BULLETS.get(topic_key, [])
        if bullets:
            layout = scene.get("layout", "centered")
            bx = self._config.width * 0.58 if "left" in layout else self._config.margin
            layers.append(
                self._bullet_layer(
                    bullets,
                    bounds=(bx, 180, 400, 200),
                    keyframes=keyframes,
                    time_s=current_time,
                    visible=visibility.get("bullets", current_time >= 0.8),
                )
            )

        layers.append(
            self._text_layer(
                "legend",
                LayerType.LEGEND,
                "Legend",
                bounds=(self._config.width - 240, self._config.height - 160, 220, 110),
                keyframes=keyframes,
                time_s=current_time,
                visible=visibility.get("legend", current_time >= 1.0),
                z=Z_INDEX["legend"],
            )
        )

        layers.append(
            self._text_layer(
                "footer",
                LayerType.FOOTER,
                scene.get("footer", DEFAULT_FOOTER),
                bounds=(self._config.margin, self._config.height - 36, 600, 20),
                keyframes=keyframes,
                time_s=current_time,
                visible=True,
                z=Z_INDEX["footer"],
            )
        )

        return [layer for layer in layers if layer.visible and layer.transform.opacity > 0.01]

    def _background_layer(self) -> RenderLayer:
        return RenderLayer(
            layer_id="background",
            layer_type=LayerType.BACKGROUND,
            bounds=(0, 0, float(self._config.width), float(self._config.height)),
            transform=TransformState(opacity=1.0),
            visible=True,
            z_index=Z_INDEX["background"],
        )

    def _asset_layer(
        self,
        asset: dict,
        keyframes: list[dict],
        time_s: float,
        visibility: dict[str, bool],
    ) -> RenderLayer | None:
        cid = asset.get("component_id", "asset")
        comp_type = asset.get("type", "asset")
        b = asset.get("bounds") or {}
        bounds = (
            float(b.get("x", 100)),
            float(b.get("y", 150)),
            float(b.get("width", 400)),
            float(b.get("height", 400)),
        )
        layer_type = LayerType.DIAGRAM if comp_type == "diagram" else LayerType.ASSET
        visible = visibility.get(cid, time_s >= 0.3)
        transform = self._transforms.transform_at(
            keyframes, cid, time_s, base_bounds=bounds
        )
        if not visible:
            transform.opacity = 0.0
        return RenderLayer(
            layer_id=cid,
            layer_type=layer_type,
            image_path=asset.get("path"),
            bounds=bounds,
            transform=transform,
            visible=visible and transform.opacity > 0.01,
            z_index=Z_INDEX.get(comp_type, 30),
        )

    def _text_layer(
        self,
        layer_id: str,
        layer_type: LayerType,
        content: str,
        *,
        bounds: tuple[float, float, float, float],
        keyframes: list[dict],
        time_s: float,
        visible: bool,
        z: int,
    ) -> RenderLayer:
        transform = self._transforms.transform_at(
            keyframes, layer_id, time_s, base_bounds=bounds
        )
        if not visible:
            transform.opacity = 0.0
        return RenderLayer(
            layer_id=layer_id,
            layer_type=layer_type,
            content=content,
            bounds=bounds,
            transform=transform,
            visible=visible and transform.opacity > 0.01,
            z_index=z,
        )

    def _bullet_layer(
        self,
        bullets: list[str],
        *,
        bounds: tuple[float, float, float, float],
        keyframes: list[dict],
        time_s: float,
        visible: bool,
    ) -> RenderLayer:
        transform = self._transforms.transform_at(
            keyframes, "bullets", time_s, base_bounds=bounds
        )
        if not visible:
            transform.opacity = 0.0
        return RenderLayer(
            layer_id="bullets",
            layer_type=LayerType.BULLETS,
            bullets=list(bullets),
            bounds=bounds,
            transform=transform,
            visible=visible and transform.opacity > 0.01,
            z_index=Z_INDEX["bullet_list"],
        )

    def _visibility_map(
        self, elements: list[dict], current_time: float
    ) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for el in elements:
            cid = el.get("component_id", "")
            start = float(el.get("start_time", 0.0))
            end = float(el.get("end_time", 999.0))
            out[cid] = start <= current_time <= end
        return out
