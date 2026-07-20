"""
Phase 5.7 — Educational Diagram Composer smoke / verification.

Run from backend/:

    python test_diagram_composer.py
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

from image_generation.diagram_composer import (  # noqa: E402
    DiagramEngine,
    earth_spec,
    human_heart_spec,
    photosynthesis_spec,
    motherboard_spec,
    dna_spec,
)


CASES = (
    ("Earth", earth_spec(concept_id="concept-earth", asset_version="v1")),
    ("Human Heart", human_heart_spec(concept_id="concept-heart", asset_version="v1")),
    ("Photosynthesis", photosynthesis_spec(concept_id="concept-photo", asset_version="v1")),
    ("Computer Motherboard", motherboard_spec(concept_id="concept-mb", asset_version="v1")),
    ("DNA", dna_spec(concept_id="concept-dna", asset_version="v1")),
)


def _find_illustration(name: str) -> Path | None:
    """Prefer processed_assets; fall back to raw_assets."""
    stem = name.lower().replace(" ", "")
    search_dirs = [
        ROOT / "processed_assets",
        ROOT / "raw_assets",
    ]
    for folder in search_dirs:
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
    draw.text((180, 240), label[:12], fill=(40, 40, 40, 255))
    img.save(path)
    return path


def main() -> int:
    engine = DiagramEngine()
    failed = 0

    print("=" * 60)
    print("Phase 5.7 — Educational Diagram Composer")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        out_root = Path(tmp) / "diagrams"
        for label, spec in CASES:
            illust = _find_illustration(spec.concept)
            if illust is None:
                illust = _make_placeholder(Path(tmp) / f"{spec.concept.replace(' ', '_')}.png", label=spec.concept)

            result = engine.compose(
                illust,
                spec,
                output_dir=out_root / spec.concept.replace(" ", "_"),
            )
            meta = result.metadata

            print()
            print(f"CONCEPT: {spec.concept}")
            print(f"  diagram_id:    {meta.diagram_id}")
            print(f"  diagram_type:  {meta.diagram_type}")
            print(f"  canvas_size:   {meta.canvas_size}")
            print(f"  labels:        {len(result.labels)}")
            print(f"  arrows:        {len(result.arrows)}")
            print(f"  legend:        {'yes' if result.legend else 'no'}")
            print(f"  png:           {result.png_path}")
            print(f"  svg:           {result.svg_path}")
            print(f"  concept_id:    {meta.concept_id}")
            print(f"  asset_version: {meta.asset_version}")

            checks = [
                (result.png_path and Path(result.png_path).is_file(), "png_export"),
                (result.svg_path and Path(result.svg_path).is_file(), "svg_export"),
                (len(result.labels) >= 1, "label_placement"),
                (len(result.arrows) >= 1, "arrow_placement"),
                (result.legend is not None and len(result.legend.items) >= 1, "legend"),
                (meta.concept_id is not None, "concept_id_metadata"),
                (meta.asset_version is not None, "asset_version_metadata"),
                (meta.canvas_size[0] > 0 and meta.canvas_size[1] > 0, "canvas_size"),
            ]
            for ok, name in checks:
                if not ok:
                    print(f"  FAIL: {name}")
                    failed += 1
                else:
                    print(f"  OK: {name}")

            # Metadata JSON on disk
            meta_path = Path(result.png_path).with_suffix(".json") if result.png_path else None
            if meta_path and meta_path.is_file():
                data = json.loads(meta_path.read_text())
                if data.get("labels") and data.get("arrows"):
                    print("  OK: metadata_json")
                else:
                    print("  FAIL: metadata_json")
                    failed += 1

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
