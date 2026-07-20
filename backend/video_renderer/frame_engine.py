"""Frame engine — render a single animation frame from Scene + Timeline JSON."""

from __future__ import annotations

from typing import Any

from PIL import Image

from image_generation.logger import get_engine_logger
from video_renderer.camera_renderer import CameraRenderer
from video_renderer.canvas import FrameCanvas
from video_renderer.compositor import Compositor
from video_renderer.frame_renderer import FrameRenderer
from video_renderer.layer_manager import LayerManager
from video_renderer.renderer_config import RendererConfig
from video_renderer.renderer_metadata import FrameRenderMetadata
from video_renderer.renderer_types import LayerType


class FrameEngine:
    """Execution layer: Scene JSON + Timeline JSON → PIL.Image at ``current_time``.

  Pipeline
  --------
  Scene → Timeline → Collect Visible Layers → Apply Transforms → Apply Camera
        → Composite Layers → Return Frame

  Future Phase 6.3: FFmpeg encodes frames to MP4 without changing this API.
    """

    def __init__(
        self,
        *,
        config: RendererConfig | None = None,
        layer_manager: LayerManager | None = None,
        frame_renderer: FrameRenderer | None = None,
        compositor: Compositor | None = None,
        camera_renderer: CameraRenderer | None = None,
        logger=None,
    ) -> None:
        self._config = config or RendererConfig()
        self._layers = layer_manager or LayerManager(config=self._config)
        self._renderer = frame_renderer or FrameRenderer(config=self._config)
        self._compositor = compositor or Compositor()
        self._camera = camera_renderer or CameraRenderer()
        self._log = logger or get_engine_logger("video_renderer")

    def render_frame(
        self,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        current_time: float,
    ) -> Image.Image:
        """Render one frame and return a PIL RGBA image."""
        self._log.info(
            "FRAME_STARTED scene_id=%s time=%.3f",
            scene.get("scene_id", "-"),
            current_time,
        )

        layers = self._layers.collect(scene, timeline, current_time)
        camera = self._camera.camera_at(
            timeline, current_time, scene_camera=scene.get("camera")
        )
        self._log.info(
            "CAMERA_APPLIED zoom=%.3f pan=%s type=%s",
            camera.zoom,
            camera.pan,
            camera.camera_type,
        )

        canvas = FrameCanvas(self._config)
        rendered: list[tuple] = []
        for layer in layers:
            if layer.layer_type == LayerType.BACKGROUND:
                canvas.image = self._renderer.render_layer(layer)
                continue
            img = self._renderer.render_layer(layer)
            rendered.append((layer, img))
            self._log.info(
                "TRANSFORM_APPLIED id=%s opacity=%.2f scale=%s",
                layer.layer_id,
                layer.transform.opacity,
                layer.transform.scale,
            )

        frame = self._compositor.composite_layers(canvas.image, rendered, camera=camera)
        frame = self._camera.apply_viewport(
            frame, camera, width=self._config.width, height=self._config.height
        )

        self._log.info(
            "FRAME_COMPLETED scene_id=%s time=%.3f layers=%s",
            scene.get("scene_id", "-"),
            current_time,
            len(layers),
        )
        return frame

    def render_frame_with_metadata(
        self,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        current_time: float,
        *,
        frame_index: int = 0,
    ) -> tuple[Image.Image, FrameRenderMetadata]:
        image = self.render_frame(scene, timeline, current_time)
        camera = self._camera.camera_at(
            timeline, current_time, scene_camera=scene.get("camera")
        )
        layers = self._layers.collect(scene, timeline, current_time)
        meta = FrameRenderMetadata(
            scene_id=str(scene.get("scene_id", "")),
            timeline_id=str(timeline.get("timeline_id", "")),
            frame_index=frame_index,
            current_time=current_time,
            visible_layers=len(layers),
            camera_zoom=camera.zoom,
            camera_pan=camera.pan,
            layer_ids=[layer.layer_id for layer in layers],
        )
        return image, meta
