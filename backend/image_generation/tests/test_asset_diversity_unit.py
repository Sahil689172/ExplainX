"""Unit tests for the Asset Diversity Manager (Task 3)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_generation.asset_diversity import (
    AssetDiversityManager,
    average_hash,
    similarity,
)


def _solid(path: Path, color) -> str:
    Image.new("RGB", (64, 64), color).save(path)
    return str(path)


def _gradient(path: Path, flip: bool = False) -> str:
    img = Image.new("L", (64, 64))
    px = img.load()
    for y in range(64):
        for x in range(64):
            v = (x * 4) % 256
            px[x, y] = 255 - v if flip else v
    img.save(path)
    return str(path)


class AssetDiversityTests(unittest.TestCase):
    def test_identical_images_are_maximally_similar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = _gradient(Path(tmp) / "a.png")
            b = _gradient(Path(tmp) / "b.png")
            self.assertAlmostEqual(similarity(average_hash(a), average_hash(b)), 1.0, places=6)

    def test_duplicate_rejected_after_register(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = _gradient(Path(tmp) / "a.png")
            dup = _gradient(Path(tmp) / "dup.png")  # visually identical
            dm = AssetDiversityManager(similarity_threshold=0.80)
            self.assertTrue(dm.register(a))
            decision = dm.evaluate(dup)
            self.assertFalse(decision.accepted)
            self.assertGreater(decision.max_similarity, 0.80)

    def test_select_prefers_diverse_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            used = _gradient(Path(tmp) / "used.png")
            near_dup = _gradient(Path(tmp) / "near.png")
            different = _gradient(Path(tmp) / "diff.png", flip=True)
            dm = AssetDiversityManager(similarity_threshold=0.80)
            dm.register(used)
            chosen = dm.select([near_dup, different])
            self.assertEqual(chosen, different)

    def test_select_falls_back_to_least_similar_when_all_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            used = _solid(Path(tmp) / "used.png", (0, 0, 0))
            d1 = _solid(Path(tmp) / "d1.png", (0, 0, 0))
            d2 = _solid(Path(tmp) / "d2.png", (0, 0, 0))
            dm = AssetDiversityManager(similarity_threshold=0.80)
            dm.register(used)
            # Every candidate identical to used -> still returns one (progress).
            self.assertIn(dm.select([d1, d2]), {d1, d2})


    def test_no_consecutive_duplicate_when_alternatives_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = _gradient(Path(tmp) / "a.png")
            b = _gradient(Path(tmp) / "b.png", flip=True)
            dm = AssetDiversityManager(similarity_threshold=0.80)
            first = dm.select_with_audit([a, b])
            dm.register(first.chosen)  # type: ignore[arg-type]
            dm._last_selected = first.chosen  # noqa: SLF001
            second = dm.select_with_audit([a, b])
            self.assertNotEqual(first.chosen, second.chosen)

    def test_select_and_register_returns_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = _gradient(Path(tmp) / "a.png")
            dm = AssetDiversityManager()
            audit = dm.select_and_register([a])
            self.assertIsInstance(audit.chosen, str)
            self.assertEqual(audit.chosen, a)


if __name__ == "__main__":
    unittest.main()
