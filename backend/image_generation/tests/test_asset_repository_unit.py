"""Unit tests for Phase 5.5 repository (offline, no OpenVINO)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_generation.repository import (
    EducationalAssetRepository,
    QualityEvaluator,
    VersionStatus,
)


def _png(path: Path, margin: int = 100) -> Path:
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for y in range(margin, 256 - margin):
        for x in range(margin, 256 - margin):
            img.putpixel((x, y), (40, 140, 220, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


class RepositoryUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "asset_library"
        self.repo = EducationalAssetRepository(root=self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_create_concept_idempotent(self) -> None:
        a = self.repo.create_concept("Volcano", subject="Geography")
        b = self.repo.create_concept("Volcano")
        self.assertEqual(a.concept_id, b.concept_id)

    def test_versions_never_overwrite(self) -> None:
        concept = self.repo.create_concept("DNA", subject="Biology")
        p = _png(Path(self._tmp.name) / "a.png")
        v1 = self.repo.create_version(
            concept=concept,
            source_png=p,
            title="DNA",
            prompt="DNA",
            enhanced_prompt="DNA educational",
        )
        concept = self.repo.get_concept(concept.concept_id)
        assert concept is not None
        v2 = self.repo.create_version(
            concept=concept,
            source_png=p,
            title="DNA",
            prompt="DNA helix",
            enhanced_prompt="DNA helix educational",
        )
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)
        self.assertTrue(
            (self.root / "concepts" / "dna" / "versions" / "v1" / "image.png").is_file()
        )
        self.assertTrue(
            (self.root / "concepts" / "dna" / "versions" / "v2" / "image.png").is_file()
        )

    def test_reject_excluded_from_best(self) -> None:
        concept = self.repo.create_concept("Heart")
        p = _png(Path(self._tmp.name) / "h.png")
        v1 = self.repo.create_version(
            concept=concept,
            source_png=p,
            title="Heart",
            prompt="Heart",
            enhanced_prompt="Heart",
        )
        self.repo.reject_version(concept.concept_id, v1.version)
        # No approved versions left
        concept2 = self.repo.create_concept("Heart")
        v2 = self.repo.create_version(
            concept=concept2,
            source_png=p,
            title="Heart",
            prompt="Heart v2",
            enhanced_prompt="Heart v2",
        )
        best = self.repo.get_best_version(concept.concept_id)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.version, v2.version)
        self.assertNotEqual(best.status, VersionStatus.REJECTED.value)

    def test_usage_persists(self) -> None:
        concept = self.repo.create_concept("Cell")
        p = _png(Path(self._tmp.name) / "c.png")
        v = self.repo.create_version(
            concept=concept,
            source_png=p,
            title="Cell",
            prompt="Cell",
            enhanced_prompt="Cell",
        )
        self.repo.record_usage(concept.concept_id, v.version)
        self.repo.record_usage(concept.concept_id, v.version)
        loaded = self.repo._require_version(concept, v.version)
        self.assertEqual(loaded.times_used, 2)
        self.assertIsNotNone(loaded.last_used)

    def test_quality_bounds(self) -> None:
        p = _png(Path(self._tmp.name) / "q.png", margin=60)
        result = QualityEvaluator().evaluate(p)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 10.0)


if __name__ == "__main__":
    unittest.main()
