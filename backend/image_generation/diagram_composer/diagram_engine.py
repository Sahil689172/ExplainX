"""Diagram engine — orchestrates layout, labels, arrows, legends, and export."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence

from PIL import Image

from image_generation.diagram_composer.arrow_engine import ArrowEngine
from image_generation.diagram_composer.canvas import (
    BackgroundMode,
    Canvas,
    fit_image_in_rect,
    load_illustration,
)
from image_generation.diagram_composer.elements import (
    DiagramMetadata,
    DiagramResult,
    DiagramSpec,
    DiagramType,
)
from image_generation.diagram_composer.export_manager import (
    ExportFormat,
    ExportManager,
    RenderContext,
)
from image_generation.diagram_composer.fixtures import get_fixture
from image_generation.diagram_composer.label_engine import LabelEngine
from image_generation.diagram_composer.layout_engine import LayoutEngine
from image_generation.diagram_composer.legend_engine import LegendEngine
from image_generation.diagram_composer.object_locator import (
    ManualObjectLocator,
    ObjectLocator,
)
from image_generation.diagram_composer.theme_manager import ThemeManager
from image_generation.logger import get_engine_logger


class DiagramEngine:
    """Transform generated illustrations into complete educational diagrams.

  Diffusion models produce illustrations only; this engine adds labels, callouts,
  arrows, and legends programmatically.

  Future: swap ``ObjectLocator`` for SAM/YOLO/GroundingDINO without API changes.
    """

    def __init__(
        self,
        *,
        layout_engine: LayoutEngine | None = None,
        label_engine: LabelEngine | None = None,
        arrow_engine: ArrowEngine | None = None,
        legend_engine: LegendEngine | None = None,
        theme_manager: ThemeManager | None = None,
        export_manager: ExportManager | None = None,
        object_locator: ObjectLocator | None = None,
        logger=None,
    ) -> None:
        self._layout = layout_engine or LayoutEngine()
        self._labels = label_engine or LabelEngine()
        self._arrows = arrow_engine or ArrowEngine()
        self._legend = legend_engine or LegendEngine()
        self._themes = theme_manager or ThemeManager()
        self._export = export_manager or ExportManager()
        self._locator = object_locator
        self._log = logger or get_engine_logger("image_generation.diagram_composer")

    def compose(
        self,
        illustration_path: str | Path,
        spec: DiagramSpec,
        *,
        output_dir: str | Path | None = None,
        export_formats: Sequence[ExportFormat] | None = None,
    ) -> DiagramResult:
        """Compose a full educational diagram from an illustration + spec."""
        path = Path(illustration_path)
        if not path.is_file():
            raise FileNotFoundError(f"Illustration not found: {path}")

        self._log.info(
            "DIAGRAM_CREATED concept=%s subject=%s type=%s",
            spec.concept,
            spec.subject,
            spec.diagram_type.value,
        )

        illustration = load_illustration(path)
        bg_mode = (
            BackgroundMode.TRANSPARENT
            if spec.transparent_background
            else BackgroundMode.THEMED
        )
        canvas = Canvas(
            width=spec.width,
            height=spec.height,
            padding=spec.padding,
            margin=spec.margin,
            background_mode=bg_mode,
        )
        canvas = canvas.auto_resize_for_image(illustration.size)

        resized, illustration_rect = fit_image_in_rect(illustration, canvas.illustration_bounds)

        # Resolve anchors: spec > locator > fixture fallback
        anchors = list(spec.anchors)
        if not anchors and self._locator is not None:
            anchors = self._locator.locate(path)
        if not anchors:
            fixture = get_fixture(spec.concept)
            if fixture:
                anchors = list(fixture.anchors)

        layout = self._layout.layout(
            anchors,
            canvas,
            illustration_rect,
            mode=spec.layout,
        )

        theme = self._themes.get(spec.theme)
        legend = None
        if spec.show_legend:
            legend_items = spec.legend_items
            if not legend_items:
                fixture = get_fixture(spec.concept)
                if fixture:
                    legend_items = fixture.legend_items
            legend = self._legend.build(
                items=legend_items,
                anchors=anchors,
                canvas=canvas,
                theme=theme,
            )

        title = spec.title or spec.concept
        ctx = RenderContext(
            canvas=canvas,
            illustration=resized,
            illustration_rect=illustration_rect,
            labels=layout.labels,
            arrows=layout.arrows,
            legend=legend,
            theme=theme,
            title=title if spec.show_title else None,
            subtitle=spec.subtitle,
            caption=spec.caption,
        )

        metadata = DiagramMetadata.create(
            concept=spec.concept,
            subject=spec.subject,
            diagram_type=spec.diagram_type,
            canvas_size=(canvas.width, canvas.height),
            labels=layout.labels,
            arrows=layout.arrows,
            theme=spec.theme,
            export_format=",".join(
                f.value for f in (export_formats or (ExportFormat.PNG, ExportFormat.SVG))
            ),
            concept_id=spec.concept_id,
            asset_version=spec.asset_version,
            illustration_path=str(path),
        )

        png_path: str | None = None
        svg_path: str | None = None
        if output_dir is not None:
            export = self._export.export(
                ctx, metadata, output_dir, formats=export_formats
            )
            png_path = export.png_path
            svg_path = export.svg_path

        return DiagramResult(
            metadata=metadata,
            png_path=png_path,
            svg_path=svg_path,
            labels=list(layout.labels),
            arrows=list(layout.arrows),
            legend=legend,
        )

    def compose_from_fixture(
        self,
        illustration_path: str | Path,
        fixture_name: str,
        *,
        output_dir: str | Path | None = None,
        concept_id: str | None = None,
        asset_version: str | None = None,
    ) -> DiagramResult:
        """Convenience: load a built-in fixture by concept name."""
        spec = get_fixture(fixture_name)
        if spec is None:
            raise ValueError(f"No diagram fixture for: {fixture_name!r}")
        spec = replace(
            spec,
            concept_id=concept_id or spec.concept_id,
            asset_version=asset_version or spec.asset_version,
        )
        return self.compose(illustration_path, spec, output_dir=output_dir)

    @staticmethod
    def infer_diagram_type(subject: str, concept: str) -> DiagramType:
        """Heuristic diagram type when caller does not specify one."""
        s = subject.lower()
        c = concept.lower()
        if "motherboard" in c or "computer" in s:
            return DiagramType.COMPUTER_ARCHITECTURE
        if "heart" in c or "anatomy" in c:
            return DiagramType.ANATOMY
        if "photosynthesis" in c or "process" in c:
            return DiagramType.PROCESS
        if "dna" in c or "biology" in s:
            return DiagramType.BIOLOGY
        if "physics" in s or "newton" in c:
            return DiagramType.PHYSICS_CONCEPT
        if "chemistry" in s or "molecule" in c:
            return DiagramType.CHEMISTRY
        if "flow" in c:
            return DiagramType.FLOW
        return DiagramType.OBJECT
