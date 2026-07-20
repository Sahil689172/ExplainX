"""Unit tests for Phase 5.7 Educational Diagram Composer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_generation.diagram_composer import (
    DiagramEngine,
    DiagramSpec,
    DiagramType,
    ManualObjectLocator,
    NullObjectLocator,
    earth_spec,
    make_anchor,
)
from image_generation.diagram_composer.arrow_engine import ArrowEngine
from image_generation.diagram_composer.canvas import Canvas
from image_generation.diagram_composer.export_manager import ExportFormat, SvgRenderer
from image_generation.diagram_composer.label_engine import LabelEngine
from image_generation.diagram_composer.layout_engine import LayoutEngine, LayoutMode


def _placeholder(path: Path) -> None:
    Image.new("RGBA", (400, 400), (230, 235, 240, 255)).save(path)


class LayoutEngineTests(unittest.TestCase):
    def test_places_labels_inside_canvas(self) -> None:
        canvas = Canvas(width=800, height=600)
        illust = canvas.illustration_bounds
        anchors = [
            make_anchor("a", "Core", x=0.5, y=0.5),
            make_anchor("b", "Mantle", x=0.4, y=0.4),
        ]
        layout = LayoutEngine().layout(
            anchors, canvas, illust, mode=LayoutMode.RADIAL
        )
        content = canvas.content_bounds
        self.assertGreaterEqual(len(layout.labels), 2)
        for label in layout.labels:
            self.assertGreaterEqual(label.bounds.left, content.left - 1)
            self.assertLessEqual(label.bounds.right, content.right + 1)
        self.assertEqual(len(layout.arrows), 2)


class LabelEngineTests(unittest.TestCase):
    def test_wrap_multiline(self) -> None:
        engine = LabelEngine()
        lines = engine.wrap("Carbon Dioxide Input Molecule", max_width=80, font_size=12)
        self.assertGreaterEqual(len(lines), 1)


class ArrowEngineTests(unittest.TestCase):
    def test_curved_path(self) -> None:
        from image_generation.diagram_composer.geometry import Point

        engine = ArrowEngine()
        arrow = engine.make_flow_arrow(
            Point(10, 10), Point(200, 100), arrow_id="f1", curved=True
        )
        path = engine.build(arrow)
        self.assertGreater(len(path.points), 2)


class DiagramEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DiagramEngine()

    def test_compose_earth_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "earth.png"
            _placeholder(img)
            spec = earth_spec(concept_id="c1", asset_version="v1")
            result = self.engine.compose(img, spec, output_dir=Path(tmp) / "out")
            self.assertTrue(result.png_path and Path(result.png_path).is_file())
            self.assertTrue(result.svg_path and Path(result.svg_path).is_file())
            self.assertEqual(result.metadata.concept_id, "c1")
            self.assertEqual(result.metadata.asset_version, "v1")
            self.assertGreater(len(result.labels), 0)
            self.assertIsNotNone(result.legend)

    def test_manual_locator(self) -> None:
        anchors = [make_anchor("x", "Test", x=0.5, y=0.5)]
        locator = ManualObjectLocator(anchors)
        self.assertEqual(len(locator.locate("any.png")), 1)
        self.assertEqual(len(NullObjectLocator().locate("any.png")), 0)

    def test_infer_diagram_type(self) -> None:
        self.assertEqual(
            DiagramEngine.infer_diagram_type("Biology", "Human Heart"),
            DiagramType.ANATOMY,
        )


class SvgRendererTests(unittest.TestCase):
    def test_svg_contains_elements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "t.png"
            _placeholder(img)
            engine = DiagramEngine()
            spec = DiagramSpec(concept="Earth", anchors=earth_spec().anchors)
            result = engine.compose(img, spec, output_dir=None)
            canvas = Canvas(width=800, height=600)
            from image_generation.diagram_composer.canvas import fit_image_in_rect, load_illustration
            from image_generation.diagram_composer.export_manager import RenderContext
            from image_generation.diagram_composer.theme_manager import ThemeManager

            illustration = load_illustration(img)
            resized, rect = fit_image_in_rect(illustration, canvas.illustration_bounds)
            ctx = RenderContext(
                canvas=canvas,
                illustration=resized,
                illustration_rect=rect,
                labels=result.labels,
                arrows=result.arrows,
                legend=result.legend,
                theme=ThemeManager().get("textbook"),
                title="Earth",
            )
            svg = SvgRenderer().render(ctx)
            self.assertIn("<svg", svg)
            self.assertIn("labels", svg)


if __name__ == "__main__":
    unittest.main()
