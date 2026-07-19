"""Phase 5.5 — Educational Asset Repository CLI / integration test (no OpenVINO required)."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

from image_generation.repository import (
    EducationalAssetRepository,
    QualityEvaluator,
    VersionStatus,
)


def _make_png(path: Path, *, color: tuple[int, int, int, int], margin: int = 80) -> Path:
    """Create a simple centered subject on transparent background."""
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    for y in range(margin, 512 - margin):
        for x in range(margin, 512 - margin):
            img.putpixel((x, y), color)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def _ok(label: str) -> None:
    print(f"{label}: OK")


def main() -> int:
    print("=" * 56)
    print("ExplainX Phase 5.5 — Educational Asset Repository")
    print("=" * 56)

    tmp = Path(tempfile.mkdtemp(prefix="explainx_repo_"))
    try:
        root = tmp / "asset_library"
        repo = EducationalAssetRepository(root=root)

        # Create concept
        concept = repo.create_concept(
            "Earth", subject="Geography", keywords=["earth", "planet", "globe"]
        )
        assert concept.total_versions == 0
        _ok("Create concept")

        # Multiple versions with different "quality" (margin affects subject size)
        v1_png = _make_png(tmp / "v1.png", color=(30, 120, 220, 255), margin=40)
        v2_png = _make_png(tmp / "v2.png", color=(20, 100, 200, 255), margin=100)
        v3_png = _make_png(tmp / "v3.png", color=(10, 90, 180, 255), margin=120)

        v1 = repo.create_version(
            concept=concept,
            source_png=v1_png,
            title="Earth",
            prompt="Earth",
            enhanced_prompt="Earth flat educational",
            generation_time_ms=1000,
            auto_approve=True,
        )
        concept = repo.get_concept(concept.concept_id)
        assert concept is not None
        v2 = repo.create_version(
            concept=concept,
            source_png=v2_png,
            title="Earth",
            prompt="Planet Earth",
            enhanced_prompt="Planet Earth flat educational",
            generation_time_ms=1100,
            auto_approve=True,
        )
        concept = repo.get_concept(concept.concept_id)
        assert concept is not None
        v3 = repo.create_version(
            concept=concept,
            source_png=v3_png,
            title="Earth",
            prompt="Blue Planet",
            enhanced_prompt="Blue Planet flat educational",
            generation_time_ms=1200,
            auto_approve=False,  # pending review
        )
        assert v1.version == 1 and v2.version == 2 and v3.version == 3
        _ok("Create multiple versions")
        _ok("Quality scoring")
        print(f"  v1={v1.quality_score} v2={v2.quality_score} v3={v3.quality_score}")

        # Approve / reject / preferred
        repo.approve_version(concept.concept_id, 3)
        _ok("Approve version")
        # Create a disposable version to reject
        bad = _make_png(tmp / "bad.png", color=(255, 0, 0, 10), margin=5)
        concept = repo.get_concept(concept.concept_id)
        assert concept is not None
        v4 = repo.create_version(
            concept=concept,
            source_png=bad,
            title="Earth",
            prompt="bad earth",
            enhanced_prompt="bad",
            auto_approve=True,
        )
        repo.reject_version(concept.concept_id, v4.version)
        rejected = repo._require_version(concept, v4.version)
        assert rejected.status == VersionStatus.REJECTED.value
        _ok("Reject version")

        # Prefer v2 explicitly
        preferred = repo.set_preferred_version(concept.concept_id, 2)
        assert preferred.preferred is True
        _ok("Preferred version")

        best = repo.get_best_version(concept.concept_id)
        assert best is not None and best.version == 2
        _ok("Best version selection")

        # Usage tracking
        before = best.times_used
        used = repo.record_usage(concept.concept_id)
        assert used is not None and used.times_used == before + 1
        used2 = repo.record_usage(concept.concept_id, 2)
        assert used2 is not None and used2.times_used == before + 2
        _ok("Usage tracking")

        # Statistics
        stats = repo.repository_statistics()
        assert stats.total_concepts >= 1
        assert stats.total_versions >= 4
        assert stats.rejected_assets >= 1
        _ok("Repository statistics")
        print("  Stats:", stats.to_dict())

        # Concept folder layout
        earth_dir = root / "concepts" / "earth"
        assert (earth_dir / "concept.json").is_file()
        assert (earth_dir / "versions" / "v1" / "image.png").is_file()
        assert (earth_dir / "versions" / "v1" / "metadata.json").is_file()
        _ok("Filesystem layout")

        # Quality evaluator standalone
        q = QualityEvaluator().evaluate(v2_png)
        assert 0.0 <= q.score <= 10.0
        _ok("QualityEvaluator")

        print("-" * 56)
        print("Educational Asset Repository: READY")
        print("=" * 56)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
