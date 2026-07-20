"""Unit tests for Phase 6.0 Frame Rendering Engine."""

from __future__ import annotations

import unittest

from PIL import Image

from video_renderer import FrameEngine, RendererConfig


SCENE = {
    "scene_id": "scene-1",
    "title": "Earth",
    "subject": "Geography",
    "layout": "left_illustration",
    "duration": 6.0,
    "camera": {"zoom": 1.05, "pan": [0, 0], "focus_region": [0.2, 0.15, 0.6, 0.65]},
    "timeline": {
        "elements": [
            {"component_id": "title", "start_time": 0.0, "end_time": 6.0},
            {"component_id": "diagram_main", "start_time": 0.5, "end_time": 6.0},
            {"component_id": "bullets", "start_time": 1.0, "end_time": 6.0},
        ]
    },
    "assets": [
        {
            "component_id": "diagram_main",
            "type": "diagram",
            "bounds": {"x": 80, "y": 160, "width": 420, "height": 420},
        }
    ],
    "bullets": ["Core", "Mantle", "Crust"],
}

TIMELINE = {
    "timeline_id": "tl-1",
    "duration": 6.0,
    "fps": 30,
    "animations": [
        {
            "target": "diagram_main",
            "animation_type": "zoom_in",
            "start_time": 0.5,
            "end_time": 2.0,
            "duration": 1.5,
        }
    ],
    "keyframes": [
        {
            "time": 0.0,
            "target": "diagram_main",
            "position": [80, 160],
            "scale": [0.9, 0.9],
            "opacity": 0.0,
            "rotation": 0.0,
        },
        {
            "time": 1.0,
            "target": "diagram_main",
            "position": [80, 160],
            "scale": [1.0, 1.0],
            "opacity": 1.0,
            "rotation": 0.0,
        },
        {
            "time": 0.0,
            "target": "__camera__",
            "camera": {"zoom": 1.0, "pan": [0, 0], "camera_type": "ken_burns"},
        },
        {
            "time": 3.0,
            "target": "__camera__",
            "camera": {"zoom": 1.08, "pan": [12, 8], "camera_type": "ken_burns"},
        },
    ],
    "camera_events": [],
}


class FrameEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = FrameEngine(config=RendererConfig(width=640, height=360))

    def test_render_frame_returns_image(self) -> None:
        img = self.engine.render_frame(SCENE, TIMELINE, 1.0)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (640, 360))
        self.assertEqual(img.mode, "RGBA")

    def test_early_frame_vs_late_frame_differ(self) -> None:
        early = self.engine.render_frame(SCENE, TIMELINE, 0.2)
        late = self.engine.render_frame(SCENE, TIMELINE, 2.5)
        self.assertNotEqual(list(early.getdata()), list(late.getdata()))

    def test_metadata(self) -> None:
        img, meta = self.engine.render_frame_with_metadata(SCENE, TIMELINE, 1.5, frame_index=3)
        self.assertEqual(meta.frame_index, 3)
        self.assertGreater(meta.visible_layers, 0)
        self.assertGreater(meta.camera_zoom, 0)


if __name__ == "__main__":
    unittest.main()
