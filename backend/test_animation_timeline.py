"""
Phase 5.9 — Animation Timeline Engine smoke / verification.

Run from backend/:

    python test_animation_timeline.py
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
    motherboard_scene,
    solar_system_scene,
)


CASES = (
    "Earth",
    "Human Heart",
    "Photosynthesis",
    "Computer Motherboard",
    "Solar System",
)

SCENE_FACTORIES = {
    "Earth": earth_scene,
    "Human Heart": human_heart_scene,
    "Photosynthesis": photosynthesis_scene,
    "Computer Motherboard": motherboard_scene,
    "Solar System": solar_system_scene,
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


def main() -> int:
    scene_engine = SceneEngine()
    timeline_engine = TimelineEngine()
    failed = 0

    print("=" * 60)
    print("Phase 5.9 — Animation Timeline Engine")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        for label in CASES:
            illust = _find_illustration(label)
            if illust is None:
                illust = _placeholder(Path(tmp) / f"{label.replace(' ', '_')}.png", label)

            factory = SCENE_FACTORIES[label]
            spec = replace(factory(), illustration_path=str(illust))
            scene_out = Path(tmp) / "scenes" / label.replace(" ", "_")
            scene_result = scene_engine.compose(spec, output_dir=scene_out)
            scene_json = scene_result.metadata.to_dict()

            anim_out = Path(tmp) / "timelines" / label.replace(" ", "_")
            result = timeline_engine.build_from_scene(
                scene_json, output_dir=anim_out
            )
            meta = result.metadata

            print()
            print(f"TOPIC: {label}")
            print(f"  timeline_id:   {meta.timeline_id}")
            print(f"  animations:    {len(meta.animations)}")
            print(f"  keyframes:     {len(meta.keyframes)}")
            print(f"  camera_events: {len(meta.camera_events)}")
            print(f"  transitions:   {len(meta.transitions)}")
            print(f"  duration:      {meta.duration}s @ {meta.fps}fps")

            checks = [
                (len(meta.animations) >= 3, "animation_count"),
                (len(meta.keyframes) >= 5, "keyframes"),
                (len(meta.camera_events) >= 1, "camera_events"),
                (len(meta.transitions) == 2, "transition_creation"),
                (meta.duration > 0, "timeline_duration"),
                (result.timeline_path and Path(result.timeline_path).is_file(), "timeline_json"),
                (result.animation_path and Path(result.animation_path).is_file(), "animation_json"),
                (meta.preset_id is not None, "preset_applied"),
            ]
            for ok, name in checks:
                if not ok:
                    print(f"  FAIL: {name}")
                    failed += 1
                else:
                    print(f"  OK: {name}")

            if result.animation_path:
                doc = json.loads(Path(result.animation_path).read_text())
                if doc.get("keyframes") and doc.get("animations"):
                    print("  OK: animation_document")
                else:
                    print("  FAIL: animation_document")
                    failed += 1

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
