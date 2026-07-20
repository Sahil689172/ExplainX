"""Scene engine — orchestrates build, layout, timeline, camera, and render."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from image_generation.logger import get_engine_logger
from scene_generation.camera import CameraPlanner
from scene_generation.scene_builder import SceneBuilder
from scene_generation.scene_layout import SceneLayoutEngine
from scene_generation.scene_metadata import (
    ComponentType,
    SceneMetadata,
    SceneResult,
    SceneSpec,
)
from scene_generation.scene_renderer import (
    SceneExportFormat,
    SceneRenderContext,
    SceneRenderer,
)
from scene_generation.scene_templates import get_fixture
from scene_generation.timeline import TimelineBuilder


class SceneEngine:
    """Compose multiple assets and diagrams into one educational scene (slide/frame).

  Pipeline: SceneSpec → SceneBuilder → SceneLayoutEngine → Timeline + Camera
            → SceneRenderer → PNG / SVG / JSON

  Future: animated camera, Ken Burns, voice sync, slide transitions — via metadata only.
    """

    def __init__(
        self,
        *,
        builder: SceneBuilder | None = None,
        layout_engine: SceneLayoutEngine | None = None,
        timeline_builder: TimelineBuilder | None = None,
        camera_planner: CameraPlanner | None = None,
        renderer: SceneRenderer | None = None,
        logger=None,
    ) -> None:
        self._builder = builder or SceneBuilder()
        self._layout = layout_engine or SceneLayoutEngine()
        self._timeline = timeline_builder or TimelineBuilder()
        self._camera = camera_planner or CameraPlanner()
        self._renderer = renderer or SceneRenderer()
        self._log = logger or get_engine_logger("scene_generation")

    def compose(
        self,
        spec: SceneSpec,
        *,
        output_dir: str | Path | None = None,
        export_formats: Sequence[SceneExportFormat] | None = None,
        compose_diagram: bool = True,
    ) -> SceneResult:
        """Build and optionally render a complete educational scene."""
        self._log.info(
            "SCENE_CREATED topic=%s title=%s scene_number=%s",
            spec.topic,
            spec.title,
            spec.scene_number,
        )

        diagram_dir = Path(output_dir) / "diagrams" if output_dir and compose_diagram else None
        spec, components = self._builder.build(
            spec,
            diagram_output_dir=diagram_dir,
        )
        placed = self._layout.layout(components, spec)

        focus = next(
            (p.bounds for p in placed if p.component.component_type in (ComponentType.ASSET, ComponentType.DIAGRAM)),
            None,
        )
        camera = self._camera.plan(
            canvas_width=spec.width,
            canvas_height=spec.height,
            focus_rect=focus,
            scene_type=spec.scene_type.value,
        )
        timeline = self._timeline.build(
            spec,
            placed,
            camera_events=camera.get("camera_events"),
        )
        self._log.info("TIMELINE_CREATED duration=%s elements=%s", timeline["duration"], len(timeline["elements"]))

        metadata = SceneMetadata.create(
            spec=spec,
            placed=placed,
            camera=camera,
            timeline=timeline,
            export_format=",".join(
                f.value for f in (export_formats or (SceneExportFormat.PNG, SceneExportFormat.SVG, SceneExportFormat.JSON))
            ),
        )

        png_path = svg_path = json_path = None
        if output_dir is not None:
            export = self._renderer.export(
                SceneRenderContext(spec=spec, placed=placed, metadata=metadata),
                output_dir,
                formats=export_formats,
            )
            png_path, svg_path, json_path = export.png_path, export.svg_path, export.json_path

        return SceneResult(
            metadata=metadata,
            placed=list(placed),
            png_path=png_path,
            svg_path=svg_path,
            json_path=json_path,
        )

    def compose_from_fixture(
        self,
        fixture_name: str,
        *,
        illustration_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        concept_id: str | None = None,
        asset_version: str | None = None,
    ) -> SceneResult:
        """Load a built-in scene fixture and compose."""
        spec = get_fixture(fixture_name)
        if spec is None:
            raise ValueError(f"No scene fixture for: {fixture_name!r}")
        from dataclasses import replace

        spec = replace(
            spec,
            illustration_path=str(illustration_path) if illustration_path else spec.illustration_path,
            concept_id=concept_id or spec.concept_id,
            asset_version=asset_version or spec.asset_version,
        )
        return self.compose(spec, output_dir=output_dir)
