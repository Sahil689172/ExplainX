"""Unit tests for Phase 6.2 Video Encoding Engine."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from video_renderer.encoder_config import OutputFormat
from video_renderer.ffmpeg_encoder import FFmpegCommand, FFmpegCommandBuilder
from video_renderer.video_encoder import FFmpegVideoEncoder, encode_video
from video_renderer.video_validator import (
    DefaultFrameValidator,
    MissingFramesError,
)
from video_renderer.thumbnail_generator import MiddleFrameThumbnailGenerator


def _write_frames(directory: Path, count: int, size: tuple[int, int] = (320, 240)) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        img = Image.new("RGBA", size, (40 + i, 80, 120, 255))
        img.save(directory / f"frame_{i:06d}.png")


class FrameValidatorTests(unittest.TestCase):
    def test_valid_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 5)
            info = DefaultFrameValidator().validate(frame_dir, fps=30)
            self.assertEqual(info.frame_count, 5)
            self.assertEqual(info.fps, 30)
            self.assertAlmostEqual(info.duration, 5 / 30)

    def test_missing_frame_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 3)
            # Remove middle frame — leaves 0 and 2, which is a gap
            (frame_dir / "frame_000001.png").unlink()
            with self.assertRaises(MissingFramesError):
                DefaultFrameValidator().validate(frame_dir, fps=24)


class FFmpegCommandBuilderTests(unittest.TestCase):
    def test_build_mp4_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 2)
            info = DefaultFrameValidator().validate(frame_dir, fps=24)
            builder = FFmpegCommandBuilder()
            cmd = builder.build(
                info,
                Path(tmp) / "out" / "video.mp4",
                output_format=OutputFormat.MP4,
                profile=__import__(
                    "video_renderer.encoding_profiles", fromlist=["get_profile"]
                ).get_profile("preview"),
            )
            joined = " ".join(cmd.command)
            self.assertIn("libx264", joined)
            self.assertIn("yuv420p", joined)
            self.assertIn("-movflags", joined)
            self.assertIn("frame_%06d.png", joined)

    def test_build_webm_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 2)
            info = DefaultFrameValidator().validate(frame_dir, fps=24)
            builder = FFmpegCommandBuilder()
            cmd = builder.build(
                info,
                Path(tmp) / "out" / "video.webm",
                output_format=OutputFormat.WEBM,
                profile=__import__(
                    "video_renderer.encoding_profiles", fromlist=["get_profile"]
                ).get_profile("preview"),
            )
            joined = " ".join(cmd.command)
            self.assertIn("libvpx-vp9", joined)
            self.assertIn("-deadline", joined)
            self.assertIn("-cpu-used", joined)
            self.assertNotIn("-preset", joined)
            self.assertNotIn("-maxrate", joined)


class MockFFmpegExecutor:
    def __init__(self) -> None:
        self.commands: list[FFmpegCommand] = []

    def is_available(self) -> bool:
        return True

    def run(self, command: FFmpegCommand, *, timeout: int = 600) -> None:
        self.commands.append(command)
        Path(command.output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(command.output_path).write_bytes(b"\x00\x00\x00\x18ftypmp42")


class VideoEncoderTests(unittest.TestCase):
    def test_encode_both_formats_with_mock_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 6)
            executor = MockFFmpegExecutor()
            encoder = FFmpegVideoEncoder(executor=executor)
            meta = encoder.encode_video(
                frame_dir,
                fps=30,
                output_format="both",
                profile="preview",
                playback_metadata={
                    "scene_id": "earth-1",
                    "scene_name": "Earth",
                    "exported_count": 6,
                },
                output_dir=Path(tmp) / "output",
            )
            self.assertEqual(len(executor.commands), 2)
            self.assertTrue(meta.mp4_path and Path(meta.mp4_path).is_file())
            self.assertTrue(meta.webm_path and Path(meta.webm_path).is_file())
            self.assertTrue(meta.thumbnail_path and Path(meta.thumbnail_path).is_file())
            self.assertEqual(meta.frame_count, 6)
            self.assertEqual(meta.fps, 30)
            self.assertAlmostEqual(meta.duration, 6 / 30)
            self.assertTrue(meta.metadata_path and Path(meta.metadata_path).is_file())
            payload = json.loads(Path(meta.metadata_path).read_text())
            self.assertEqual(payload["scene_name"], "Earth")

    def test_public_encode_video_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 3)
            mock_encoder = MagicMock()
            mock_encoder.encode_video.return_value = MagicMock(video_id="v1")
            result = encode_video(
                frame_dir,
                24,
                "mp4",
                "preview",
                encoder=mock_encoder,
            )
            mock_encoder.encode_video.assert_called_once()
            self.assertEqual(result.video_id, "v1")


class ThumbnailGeneratorTests(unittest.TestCase):
    def test_middle_frame_thumbnail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame_dir = Path(tmp) / "frames"
            _write_frames(frame_dir, 5)
            info = DefaultFrameValidator().validate(frame_dir, fps=30)
            thumb_path = MiddleFrameThumbnailGenerator().generate(
                info, Path(tmp) / "thumbnail.png"
            )
            self.assertTrue(Path(thumb_path).is_file())
            with Image.open(thumb_path) as img:
                self.assertEqual(img.size, (320, 240))


if __name__ == "__main__":
    unittest.main()
