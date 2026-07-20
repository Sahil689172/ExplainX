"""Unit tests for SceneCollection frame stitching (Task 1/2)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from video_renderer.playback_metadata import PlaybackMetadata
from video_renderer.scene_collection import SceneClip, SceneCollection


def _write_frames(directory: Path, count: int, *, color=(10, 20, 30)) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        p = directory / f"frame_{i:06d}.png"
        Image.new("RGB", (32, 18), color).save(p)
        paths.append(str(p))
    return paths


class _FakePlayer:
    """Stand-in TimelinePlayer that renders N flat frames per scene."""

    def __init__(self, frames_per_scene: dict[str, int], fps: int = 30) -> None:
        self._frames = frames_per_scene
        self._fps = fps

    def play_timeline(self, scene, timeline, *, output_dir, fps=None, **_kw):
        name = scene["title"]
        count = self._frames[name]
        out = Path(output_dir) / "frames"
        files = _write_frames(out, count)
        return PlaybackMetadata.create(
            session_id="s",
            scene_id=name,
            scene_name=name,
            fps=fps or self._fps,
            duration=count / (fps or self._fps),
            frame_count=count,
            exported_count=count,
            output_directory=str(out),
            render_time_seconds=0.0,
            frame_files=files,
        )


class SceneCollectionTests(unittest.TestCase):
    def test_frames_merge_into_one_continuous_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            player = _FakePlayer({"A": 3, "B": 2, "C": 4}, fps=30)
            collection = SceneCollection(player)
            for name, n in (("A", 3), ("B", 2), ("C", 4)):
                collection.add(SceneClip(name=name, scene={"title": name},
                                         animation={"fps": 30}, fps=30))

            merged = collection.render(Path(tmp) / "merged",
                                       scratch_dir=Path(tmp) / "scratch")

            self.assertEqual(merged.frame_count, 9)  # 3 + 2 + 4
            self.assertEqual(merged.fps, 30)
            self.assertAlmostEqual(merged.duration, 9 / 30, places=3)

            # Continuous, zero-padded, no gaps.
            files = sorted((merged.frame_directory).glob("frame_*.png"))
            self.assertEqual(len(files), 9)
            self.assertEqual(files[0].name, "frame_000000.png")
            self.assertEqual(files[-1].name, "frame_000008.png")

            # Per-scene ranges are contiguous.
            self.assertEqual([(s.frame_start, s.frame_end) for s in merged.scenes],
                             [(0, 2), (3, 4), (5, 8)])
            for s in merged.scenes:
                self.assertTrue(s.frame_match)
                self.assertEqual(s.expected_frames, s.frame_count)

    def test_empty_collection_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                SceneCollection(_FakePlayer({})).render(Path(tmp) / "m")


if __name__ == "__main__":
    unittest.main()
