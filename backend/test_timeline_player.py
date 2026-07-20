"""
Phase 6.1 — Timeline Playback Engine smoke / verification.

Run from backend/:

    python test_timeline_player.py
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
from video_renderer import (  # noqa: E402
    FpsManager,
    TimelinePlayer,
)
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
    player = TimelinePlayer()
    fps_mgr = FpsManager()
    failed = 0

    print("=" * 60)
    print("Phase 6.1 — Timeline Playback Engine")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        for label in CASES:
            scene_json, animation_json = _prepare_scene_timeline(label, tmp)
            duration = float(animation_json.get("duration", scene_json.get("duration", 5.0)))
            fps = fps_mgr.resolve(animation_json.get("fps"))
            expected_total = fps_mgr.frame_count(duration, fps)

            print()
            print(f"TOPIC: {label}")
            print(f"  duration={duration}s fps={fps} expected_total_frames={expected_total}")

            # Frame range render (first 5 frames) — fast verification
            out_dir = Path(tmp) / "output" / label.replace(" ", "_")
            meta = player.play_timeline(
                scene_json,
                animation_json,
                output_dir=out_dir,
                fps=fps,
                frame_end=4,
            )

            print(f"  exported={meta.exported_count} dir={meta.output_directory}")

            checks = [
                (meta.frame_count == expected_total, "frame_count"),
                (meta.exported_count == 5, "exported_range"),
                (Path(meta.output_directory).is_dir(), "export_directory"),
                (Path(meta.frame_files[0]).name == "frame_000000.png", "frame_numbering"),
                (abs(meta.timestamps[1] - 1 / fps) < 0.001, "timestamps"),
                (meta.session_id and meta.scene_id, "metadata_ids"),
                (meta.render_time_seconds >= 0, "render_time"),
            ]
            for ok, name in checks:
                if not ok:
                    print(f"  FAIL: {name}")
                    failed += 1
                else:
                    print(f"  OK: {name}")

            # Preview mode — fewer exports than full range would imply
            preview_out = Path(tmp) / "output_preview" / label.replace(" ", "_")
            preview_meta = player.play_preview(
                scene_json,
                animation_json,
                output_dir=preview_out,
                preview_mode=0.25,
                fps=fps,
            )
            if preview_meta.exported_count < expected_total:
                print("  OK: preview_mode")
            else:
                print("  FAIL: preview_mode")
                failed += 1

        # FPS variants
        scene_json, animation_json = _prepare_scene_timeline("Earth", tmp)
        for test_fps in (24, 30, 60):
            dur = float(animation_json["duration"])
            count = fps_mgr.frame_count(dur, test_fps)
            ts1 = fps_mgr.timestamp_for_frame(1, test_fps)
            expected_ts = round(1 / test_fps, 6)
            if count > 0 and abs(ts1 - expected_ts) < 0.0001:
                print(f"  OK: fps_{test_fps}")
            else:
                print(f"  FAIL: fps_{test_fps}")
                failed += 1

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
