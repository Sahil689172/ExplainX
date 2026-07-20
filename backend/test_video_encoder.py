"""
Phase 6.2 — Video Encoding Engine smoke / verification.

Run from backend/:

    python test_video_encoder.py

Requires FFmpeg on PATH for full encoding checks.
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from animation import TimelineEngine  # noqa: E402
from scene_generation import (  # noqa: E402
    SceneEngine,
    earth_scene,
    human_heart_scene,
    photosynthesis_scene,
    solar_system_scene,
)
from video_renderer import TimelinePlayer, encode_video  # noqa: E402
from video_renderer.ffmpeg_encoder import SubprocessFFmpegExecutor  # noqa: E402
from video_renderer.renderer_config import TOPIC_BULLETS  # noqa: E402


CASES = (
    "Earth",
    "Human Heart",
    "Solar System",
    "Photosynthesis",
)

FACTORIES = {
    "Earth": earth_scene,
    "Human Heart": human_heart_scene,
    "Solar System": solar_system_scene,
    "Photosynthesis": photosynthesis_scene,
}


def _find_illustration(name: str) -> Path | None:
    stem = name.lower().replace(" ", "")
    for folder in (ROOT / "processed_assets", ROOT / "raw_assets"):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            low = path.name.lower()
            if stem in low.replace("_", "").replace(" ", ""):
                return path
            if name.lower().split()[0] in low:
                return path
    return None


def _placeholder(path: Path, label: str) -> Path:
    img = Image.new("RGBA", (512, 512), (240, 245, 250, 255))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    draw.ellipse((96, 96, 416, 416), fill=(180, 200, 220, 255), outline=(80, 100, 130, 255), width=3)
    draw.text((160, 240), label[:12], fill=(40, 40, 40, 255))
    img.save(path)
    return path


def _prepare_scene_timeline(label: str, tmp: str) -> tuple[dict, dict]:
    illust = _find_illustration(label)
    if illust is None:
        illust = _placeholder(Path(tmp) / f"{label.replace(' ', '_')}.png", label)

    spec = replace(FACTORIES[label](), illustration_path=str(illust))
    scene_engine = SceneEngine()
    timeline_engine = TimelineEngine()

    scene_dir = Path(tmp) / "scenes" / label.replace(" ", "_")
    scene_result = scene_engine.compose(spec, output_dir=scene_dir)
    scene_json = scene_result.metadata.to_dict()
    scene_json["bullets"] = TOPIC_BULLETS.get(label.lower(), [])

    timeline_dir = Path(tmp) / "timelines" / label.replace(" ", "_")
    tl_result = timeline_engine.build_from_scene(scene_json, output_dir=timeline_dir)
    animation_json = json.loads(Path(tl_result.animation_path).read_text())
    return scene_json, animation_json


def main() -> int:
    ffmpeg = SubprocessFFmpegExecutor()
    if not ffmpeg.is_available():
        print("SKIP: FFmpeg not found on PATH — install FFmpeg to run encoding checks")
        return 0

    player = TimelinePlayer()
    failed = 0

    print("=" * 60)
    print("Phase 6.2 — Video Encoding Engine")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        for label in CASES:
            scene_json, animation_json = _prepare_scene_timeline(label, tmp)
            fps = int(animation_json.get("fps", 30))

            print()
            print(f"TOPIC: {label}")

            frames_out = Path(tmp) / "frames" / label.replace(" ", "_")
            playback_meta = player.play_timeline(
                scene_json,
                animation_json,
                output_dir=frames_out,
                fps=fps,
                frame_end=11,
            )

            video_meta = encode_video(
                playback_meta.output_directory,
                fps=playback_meta.fps,
                output_format="both",
                profile="preview",
                playback_metadata=playback_meta,
                output_dir=Path(tmp) / "output",
            )

            expected_duration = playback_meta.exported_count / playback_meta.fps
            video_dir = Path(video_meta.output_directory)

            checks = [
                (video_meta.mp4_path and Path(video_meta.mp4_path).is_file(), "mp4_created"),
                (video_meta.webm_path and Path(video_meta.webm_path).is_file(), "webm_created"),
                (video_meta.thumbnail_path and Path(video_meta.thumbnail_path).is_file(), "thumbnail"),
                (video_meta.metadata_path and Path(video_meta.metadata_path).is_file(), "metadata_json"),
                (video_meta.fps == playback_meta.fps, "fps"),
                (video_meta.frame_count == playback_meta.exported_count, "frame_count"),
                (abs(video_meta.duration - expected_duration) < 0.01, "duration"),
                (video_dir.name == label.replace(" ", "_") or label.replace(" ", "_") in video_dir.as_posix(), "export_layout"),
            ]

            for ok, name in checks:
                if not ok:
                    print(f"  FAIL: {name}")
                    failed += 1
                else:
                    print(f"  OK: {name}")

            print(f"  video_dir={video_dir}")

        # Quick profile smoke
        scene_json, animation_json = _prepare_scene_timeline("Earth", tmp)
        frames_out = Path(tmp) / "frames" / "Earth_profile"
        meta = player.play_timeline(
            scene_json, animation_json, output_dir=frames_out, fps=30, frame_end=5
        )
        for profile in ("preview", "standard"):
            v = encode_video(
                meta.output_directory,
                fps=meta.fps,
                output_format="mp4",
                profile=profile,
                playback_metadata=meta,
                output_dir=Path(tmp) / "output_profiles",
            )
            if v.render_profile == profile and Path(v.mp4_path).is_file():
                print(f"  OK: profile_{profile}")
            else:
                print(f"  FAIL: profile_{profile}")
                failed += 1

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
