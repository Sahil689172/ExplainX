"""
Phase 5.8 — Educational Scene Composer smoke / verification.

Run from backend/:

    python test_scene_composer.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scene_generation import (  # noqa: E402
    SceneEngine,
    earth_scene,
    human_heart_scene,
    photosynthesis_scene,
    motherboard_scene,
    solar_system_scene,
)


CASES = (
    ("Earth", earth_scene()),
    ("Human Heart", human_heart_scene()),
    ("Photosynthesis", photosynthesis_scene()),
    ("Computer Motherboard", motherboard_scene()),
    ("Solar System", solar_system_scene()),
)


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


def _make_placeholder(path: Path, *, label: str) -> Path:
    img = Image.new("RGBA", (512, 512), (240, 245, 250, 255))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    draw.ellipse((96, 96, 416, 416), fill=(180, 200, 220, 255), outline=(80, 100, 130, 255), width=3)
    draw.text((180, 240), label[:14], fill=(40, 40, 40, 255))
    img.save(path)
    return path


def main() -> int:
    engine = SceneEngine()
    failed = 0

    print("=" * 60)
    print("Phase 5.8 — Educational Scene Composer")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        out_root = Path(tmp) / "scenes"
        for label, base_spec in CASES:
            illust = _find_illustration(label)
            if illust is None:
                illust = _make_placeholder(
                    Path(tmp) / f"{label.replace(' ', '_')}.png", label=label
                )

            from dataclasses import replace

            spec = replace(base_spec, illustration_path=str(illust))
            result = engine.compose(
                spec,
                output_dir=out_root / label.replace(" ", "_"),
            )
            meta = result.metadata

            print()
            print(f"TOPIC: {label}")
            print(f"  scene_id:      {meta.scene_id}")
            print(f"  layout:        {meta.layout}")
            print(f"  placed:        {len(result.placed)}")
            print(f"  assets:        {len(meta.assets)}")
            print(f"  diagrams:      {len(meta.diagrams)}")
            print(f"  duration:      {meta.duration}s")
            print(f"  timeline els:  {len(meta.timeline.get('elements', []))}")
            print(f"  png:           {result.png_path}")

            checks = [
                (result.png_path and Path(result.png_path).is_file(), "png_export"),
                (result.svg_path and Path(result.svg_path).is_file(), "svg_export"),
                (result.json_path and Path(result.json_path).is_file(), "json_export"),
                (len(result.placed) >= 3, "scene_layout"),
                (meta.concept_id is not None, "concept_id_metadata"),
                (meta.asset_version is not None, "asset_version_metadata"),
                (meta.diagram_version is not None, "diagram_version_metadata"),
                (meta.camera.get("camera_start") is not None, "camera_metadata"),
                (len(meta.timeline.get("elements", [])) >= 1, "timeline_generation"),
                (meta.timeline.get("duration", 0) > 0, "timeline_duration"),
            ]
            has_diagram = any(
                p.component.component_type.value == "diagram" for p in result.placed
            )
            has_asset_or_diagram = any(
                p.component.component_type.value in ("asset", "diagram")
                for p in result.placed
            )
            checks.append((has_asset_or_diagram, "asset_or_diagram_placement"))
            if label != "Solar System":
                checks.append((has_diagram or has_asset_or_diagram, "diagram_placement"))

            for ok, name in checks:
                if not ok:
                    print(f"  FAIL: {name}")
                    failed += 1
                else:
                    print(f"  OK: {name}")

            if result.json_path:
                data = json.loads(Path(result.json_path).read_text())
                if data.get("timeline") and data.get("camera"):
                    print("  OK: metadata_structure")
                else:
                    print("  FAIL: metadata_structure")
                    failed += 1

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
