"""Unit tests for Phase 5.9 Animation Timeline Engine."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from animation import TimelineEngine, get_preset
from animation.animation_metadata import AnimationType
from animation.easing import Easing


SAMPLE_SCENE = {
    "scene_id": "test-scene-1",
    "title": "Earth",
    "duration": 6.0,
    "camera": {
        "zoom": 1.05,
        "pan": [0.0, 0.0],
        "camera_start": [640, 360],
        "camera_end": [700, 380],
        "focus_region": [0.2, 0.15, 0.6, 0.65],
        "camera_events": [
            {"time_seconds": 0.0, "zoom": 1.0, "pan": [0, 0]},
            {"time_seconds": 3.0, "zoom": 1.08, "pan": [20, 10]},
        ],
    },
    "timeline": {
        "duration": 6.0,
        "elements": [
            {
                "component_id": "title",
                "component_type": "title",
                "start_time": 0.0,
                "duration": 6.0,
                "end_time": 6.0,
            },
            {
                "component_id": "diagram_main",
                "component_type": "diagram",
                "start_time": 0.5,
                "duration": 5.5,
                "end_time": 6.0,
            },
            {
                "component_id": "bullets",
                "component_type": "bullet_list",
                "start_time": 1.0,
                "duration": 5.0,
                "end_time": 6.0,
            },
        ],
    },
    "assets": [
        {
            "component_id": "diagram_main",
            "type": "diagram",
            "bounds": {"x": 200, "y": 150, "width": 400, "height": 400},
        }
    ],
}


class TimelineEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TimelineEngine()

    def test_build_from_scene(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.engine.build_from_scene(SAMPLE_SCENE, output_dir=tmp)
            meta = result.metadata
            self.assertGreater(len(meta.animations), 3)
            self.assertGreater(len(meta.keyframes), 5)
            self.assertGreaterEqual(len(meta.camera_events), 1)
            self.assertEqual(len(meta.transitions), 2)
            self.assertTrue(Path(result.timeline_path).is_file())
            self.assertTrue(Path(result.animation_path).is_file())

    def test_preset_for_topic(self) -> None:
        preset = get_preset(topic="Photosynthesis")
        self.assertEqual(preset.preset_id, "process_flow")

    def test_easing(self) -> None:
        e = Easing()
        self.assertAlmostEqual(e.interpolate(0.0), 0.0)
        self.assertAlmostEqual(e.interpolate(1.0), 1.0)

    def test_animation_types_in_output(self) -> None:
        result = self.engine.build_from_scene(SAMPLE_SCENE)
        types = {a["animation_type"] for a in result.metadata.animations}
        self.assertTrue(types & {AnimationType.FADE_IN.value, AnimationType.ZOOM_IN.value})

    def test_build_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene.json"
            path.write_text(json.dumps(SAMPLE_SCENE), encoding="utf-8")
            result = self.engine.build_from_file(path, output_dir=tmp)
            self.assertEqual(result.metadata.scene_id, "test-scene-1")


if __name__ == "__main__":
    unittest.main()
