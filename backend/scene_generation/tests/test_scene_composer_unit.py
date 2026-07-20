"""Unit tests for Phase 5.8 Educational Scene Composer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scene_generation import (
    SceneEngine,
    SceneLayout,
    SceneSpec,
    SceneType,
    earth_scene,
)
from scene_generation.camera import CameraPlanner
from scene_generation.scene_metadata import ComponentType
from scene_generation.timeline import TimelineBuilder


def _placeholder(path: Path) -> None:
    Image.new("RGBA", (400, 400), (230, 235, 240, 255)).save(path)


class SceneEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SceneEngine()

    def test_compose_earth_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "earth.png"
            _placeholder(img)
            from dataclasses import replace

            spec = replace(earth_scene(), illustration_path=str(img))
            result = self.engine.compose(spec, output_dir=Path(tmp) / "out")
            self.assertTrue(result.png_path and Path(result.png_path).is_file())
            self.assertTrue(result.svg_path and Path(result.svg_path).is_file())
            self.assertTrue(result.json_path and Path(result.json_path).is_file())
            self.assertEqual(result.metadata.concept_id, "concept-earth")
            self.assertGreater(len(result.metadata.timeline["elements"]), 0)

    def test_timeline_has_appearance_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "t.png"
            _placeholder(img)
            from dataclasses import replace

            spec = replace(
                SceneSpec(topic="Test", title="Test Scene", layout=SceneLayout.CENTERED),
                illustration_path=str(img),
            )
            result = self.engine.compose(spec, output_dir=None, compose_diagram=False)
            order = result.metadata.timeline.get("appearance_order", [])
            self.assertGreaterEqual(len(order), 1)

    def test_camera_metadata(self) -> None:
        cam = CameraPlanner().plan(canvas_width=1280, canvas_height=720)
        self.assertIn("zoom", cam)
        self.assertIn("camera_events", cam)


class SceneLayoutTests(unittest.TestCase):
    def test_two_column_layout(self) -> None:
        from scene_generation.scene_builder import SceneBuilder
        from scene_generation.scene_layout import SceneLayoutEngine

        spec = SceneSpec(
            topic="Compare",
            title="Compare",
            layout=SceneLayout.TWO_COLUMN,
            bullets=["A", "B"],
        )
        _, components = SceneBuilder().build(spec)
        placed = SceneLayoutEngine().layout(components, spec)
        types = {p.component.component_type for p in placed}
        self.assertIn(ComponentType.TITLE, types)


if __name__ == "__main__":
    unittest.main()
