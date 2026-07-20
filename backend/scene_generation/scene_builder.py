"""Scene builder — assemble components from spec, assets, and diagrams."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from image_generation.diagram_composer.diagram_engine import DiagramEngine
from image_generation.diagram_composer.fixtures import get_fixture as get_diagram_fixture
from image_generation.logger import get_engine_logger
from scene_generation.scene_metadata import ComponentType, SceneComponent, SceneSpec
from scene_generation.scene_templates import apply_template


class SceneBuilder:
    """Build logical scene components before layout.

    Optionally invokes :class:`DiagramEngine` when an illustration is provided
    but no pre-rendered diagram exists.
    """

    def __init__(
        self,
        *,
        diagram_engine: DiagramEngine | None = None,
        logger: Any | None = None,
    ) -> None:
        self._diagrams = diagram_engine or DiagramEngine()
        self._log = logger or get_engine_logger("scene_generation")

    def build(self, spec: SceneSpec, *, diagram_output_dir: Path | None = None) -> tuple[SceneSpec, list[SceneComponent]]:
        if spec.template_id:
            spec = apply_template(spec, spec.template_id)

        components: list[SceneComponent] = [
            SceneComponent("bg", ComponentType.BACKGROUND, z_index=0),
            SceneComponent("title", ComponentType.TITLE, content=spec.title, z_index=1),
        ]
        if spec.subtitle:
            components.append(
                SceneComponent("subtitle", ComponentType.SUBTITLE, content=spec.subtitle, z_index=2)
            )

        asset_path = spec.asset_path
        diagram_path = spec.diagram_path

        if diagram_path is None and spec.illustration_path:
            diagram_path = self._maybe_compose_diagram(
                spec, Path(spec.illustration_path), diagram_output_dir
            )

        if diagram_path:
            components.append(
                SceneComponent(
                    "diagram_main",
                    ComponentType.DIAGRAM,
                    image_path=str(diagram_path),
                    concept_id=spec.concept_id,
                    asset_version=spec.asset_version,
                    diagram_version=spec.diagram_version or "v1",
                    z_index=4,
                )
            )
        elif asset_path or spec.illustration_path:
            path = asset_path or spec.illustration_path
            components.append(
                SceneComponent(
                    "asset_main",
                    ComponentType.ASSET,
                    image_path=str(path),
                    concept_id=spec.concept_id,
                    asset_version=spec.asset_version,
                    z_index=3,
                )
            )

        if spec.bullets:
            components.append(
                SceneComponent(
                    "bullets",
                    ComponentType.BULLET_LIST,
                    bullets=list(spec.bullets),
                    z_index=5,
                )
            )

        components.append(
            SceneComponent(
                "legend",
                ComponentType.LEGEND,
                content="Legend",
                z_index=6,
            )
        )

        if spec.caption:
            components.append(
                SceneComponent("caption", ComponentType.CAPTION, content=spec.caption, z_index=7)
            )
        if spec.footer:
            components.append(
                SceneComponent("footer", ComponentType.FOOTER, content=spec.footer, z_index=8)
            )

        return spec, components

    def _maybe_compose_diagram(
        self,
        spec: SceneSpec,
        illustration: Path,
        output_dir: Path | None,
    ) -> str | None:
        fixture = get_diagram_fixture(spec.topic)
        if fixture is None:
            return None
        from dataclasses import replace

        diagram_spec = replace(
            fixture,
            concept_id=spec.concept_id,
        )
        out = output_dir or illustration.parent / "diagrams"
        result = self._diagrams.compose(illustration, diagram_spec, output_dir=out)
        return result.png_path
