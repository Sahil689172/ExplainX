"""Unit tests for Phase 6.1 Timeline Playback Engine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from video_renderer import (
    FpsManager,
    FrameExporter,
    FrameScheduler,
    PlaybackMode,
    PlaybackRequest,
    PlaybackController,
    TimelinePlayer,
)


SCENE = {"scene_id": "s1", "title": "Earth", "duration": 2.0}
TIMELINE = {"timeline_id": "t1", "duration": 2.0, "fps": 30, "keyframes": []}


class FpsManagerTests(unittest.TestCase):
    def test_frame_count_30fps(self) -> None:
        mgr = FpsManager()
        self.assertEqual(mgr.frame_count(2.0, 30), 60)
        self.assertAlmostEqual(mgr.timestamp_for_frame(1, 30), 0.033333, places=5)

    def test_supported_fps(self) -> None:
        mgr = FpsManager()
        for fps in (24, 30, 60):
            self.assertEqual(mgr.resolve(fps), fps)


class FrameSchedulerTests(unittest.TestCase):
    def test_preview_skips_frames(self) -> None:
        sched = FrameScheduler()
        full = sched.schedule(duration=1.0, fps=30, preview_mode=1.0)
        preview = sched.schedule(duration=1.0, fps=30, preview_mode=0.25)
        self.assertGreater(len(full), len(preview))

    def test_frame_range(self) -> None:
        sched = FrameScheduler()
        frames = sched.schedule(duration=2.0, fps=30, frame_start=0, frame_end=4)
        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[0].export_index, 0)
        self.assertEqual(frames[-1].frame_index, 4)


class FrameExporterTests(unittest.TestCase):
    def test_naming(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exporter = FrameExporter()
            img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
            path = exporter.export(img, tmp, 0)
            self.assertTrue(path.endswith("frame_000000.png"))


class TimelinePlayerTests(unittest.TestCase):
    def test_play_timeline_with_mock_engine(self) -> None:
        mock_engine = MagicMock()
        mock_engine.render_frame.return_value = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        player = TimelinePlayer(frame_engine=mock_engine)

        with tempfile.TemporaryDirectory() as tmp:
            meta = player.play_timeline(
                SCENE,
                TIMELINE,
                output_dir=tmp,
                fps=30,
                frame_end=2,
            )
            self.assertEqual(meta.exported_count, 3)
            self.assertEqual(mock_engine.render_frame.call_count, 3)
            self.assertTrue(Path(meta.frame_files[0]).is_file())

    def test_playback_controller_time_range(self) -> None:
        ctrl = PlaybackController()
        req = PlaybackRequest(mode=PlaybackMode.TIME_RANGE, time_start=0.0, time_end=0.1, fps=30)
        schedule, fps, duration, total = ctrl.plan(SCENE, TIMELINE, req)
        self.assertEqual(fps, 30)
        self.assertGreater(len(schedule), 0)
        self.assertLessEqual(schedule[-1].timestamp, 0.1 + 0.001)


if __name__ == "__main__":
    unittest.main()
