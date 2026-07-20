"""
Phase 6.0 — Frame Rendering Engine smoke / verification.

Run from backend/:

    python test_frame_renderer.py
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
from video_renderer import FrameEngine  # noqa: E402
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

FRAME_TIMES = (0.0, 0.5, 1.0, 2.0, 3.0)


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


def main() -> int:
    scene_engine = SceneEngine()
    timeline_engine = TimelineEngine()
    frame_engine = FrameEngine()
    failed = 0

    print("=" * 60)
    print("Phase 6.0 — Frame Rendering Engine")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        for label in CASES:
            illust = _find_illustration(label)
            if illust is None:
                illust = _placeholder(Path(tmp) / f"{label.replace(' ', '_')}.png", label)

            spec = replace(FACTORIES[label](), illustration_path=str(illust))
            scene_dir = Path(tmp) / "scenes" / label.replace(" ", "_")
            scene_result = scene_engine.compose(spec, output_dir=scene_dir)
            scene_json = scene_result.metadata.to_dict()
            scene_json["bullets"] = TOPIC_BULLETS.get(label.lower(), [])

            timeline_dir = Path(tmp) / "timelines" / label.replace(" ", "_")
            tl_result = timeline_engine.build_from_scene(scene_json, output_dir=timeline_dir)
            animation_json = json.loads(Path(tl_result.animation_path).read_text())

            out_dir = Path(tmp) / "frames" / label.replace(" ", "_")
            out_dir.mkdir(parents=True, exist_ok=True)

            frames: list[Image.Image] = []
            opacities: list[float] = []
            print()
            print(f"TOPIC: {label}")

            for i, t in enumerate(FRAME_TIMES):
                frame, meta = frame_engine.render_frame_with_metadata(
                    scene_json, animation_json, t, frame_index=i
                )
                path = out_dir / f"frame_{i:03d}.png"
                frame.save(path)
                frames.append(frame)
                opacities.append(meta.camera_zoom)
                print(
                    f"  frame_{i:03d}.png  t={t:.1f}s  layers={meta.visible_layers}  zoom={meta.camera_zoom:.3f}"
                )

            checks = [
                (all(p.is_file() for p in out_dir.glob("frame_*.png")), "frames_exported"),
                (len(frames) == 5, "five_frames"),
                (frames[0].size == (1280, 720), "canvas_size"),
                (any(m > 0 for m in opacities), "camera_applied"),
                (animation_json.get("keyframes"), "timeline_keyframes"),
                (len(animation_json.get("animations", [])) >= 3, "animations_present"),
            ]
            # Opacity should change across frames (fade/zoom animations)
            if frames[0].getbbox() and frames[-1].getbbox():
                checks.append((True, "layers_visible"))
            else:
                checks.append((False, "layers_visible"))

            for ok, name in checks:
                if not ok:
                    print(f"  FAIL: {name}")
                    failed += 1
                else:
                    print(f"  OK: {name}")

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
