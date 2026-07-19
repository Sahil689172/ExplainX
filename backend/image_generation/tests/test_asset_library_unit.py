"""Unit tests for Phase 5.4 keyword search / expansion (no OpenVINO)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from PIL import Image

from image_generation.asset_index import AssetMetadata, _utc_now_iso
from image_generation.asset_library import SmartAssetLibrary
from image_generation.asset_search import KeywordSearcher, SearchQuery
from image_generation.keyword_expand import expand_keywords, expand_from_prompt
from image_generation.prompt_enhancer import PromptEnhancer


class KeywordExpandTests(unittest.TestCase):
    def test_earth_expansions(self) -> None:
        keys = expand_keywords("Earth")
        self.assertIn("earth", keys)
        self.assertIn("globe", keys)
        self.assertIn("blue planet", keys)

    def test_heart_expansions(self) -> None:
        keys = expand_from_prompt("diagram of the human heart", title="Heart")
        self.assertTrue(any("heart" in k for k in keys))
        self.assertTrue(any("cardiac" in k for k in keys))


class KeywordSearcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.earth = AssetMetadata(
            id=str(uuid4()),
            title="Earth",
            category="Geography",
            keywords=["earth", "planet", "globe", "world", "blue planet"],
            style="flat_vector",
            background="transparent",
            width=512,
            height=512,
            created_at=_utc_now_iso(),
            generator="test",
            prompt="earth",
            enhanced_prompt="earth flat",
            file_path="asset_library/assets/fake.png",
        )
        self.heart = AssetMetadata(
            id=str(uuid4()),
            title="Heart",
            category="Biology",
            keywords=["heart", "human heart", "cardiac", "cardiac organ"],
            style="flat_vector",
            background="transparent",
            width=512,
            height=512,
            created_at=_utc_now_iso(),
            generator="test",
            prompt="heart",
            enhanced_prompt="heart flat",
            file_path="asset_library/assets/fake2.png",
        )
        self.searcher = KeywordSearcher([self.earth, self.heart])

    def test_exact_title(self) -> None:
        hits = self.searcher.search(SearchQuery(text="Earth", title="Earth"))
        self.assertTrue(hits)
        self.assertEqual(hits[0].asset.id, self.earth.id)
        self.assertEqual(hits[0].match_kind, "exact_title")

    def test_planet_earth_similar(self) -> None:
        hits = self.searcher.search(
            SearchQuery(text="Planet Earth", title="Planet Earth")
        )
        self.assertTrue(hits)
        self.assertEqual(hits[0].asset.id, self.earth.id)

    def test_blue_planet(self) -> None:
        hits = self.searcher.search(SearchQuery(text="Blue Planet", title="Blue Planet"))
        self.assertTrue(hits)
        self.assertEqual(hits[0].asset.id, self.earth.id)

    def test_cardiac_organ(self) -> None:
        hits = self.searcher.search(
            SearchQuery(text="Cardiac Organ", title="Cardiac Organ")
        )
        self.assertTrue(hits)
        self.assertEqual(hits[0].asset.id, self.heart.id)


class PromptEnhancerTests(unittest.TestCase):
    def test_earth_title(self) -> None:
        enh = PromptEnhancer().enhance(
            "A flat educational illustration of Earth with transparent background."
        )
        self.assertIn("Earth", enh["title"])
        self.assertEqual(enh["category"], "Geography")


class SmartAssetLibraryTests(unittest.TestCase):
    def test_save_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "asset_library"
            lib = SmartAssetLibrary(root=root)
            src = Path(tmp) / "src.png"
            Image.new("RGBA", (64, 64), (0, 128, 255, 255)).save(src)

            a1 = lib.save_new_asset(
                source_png=src,
                title="Earth",
                prompt="Earth",
                enhanced_prompt="Earth flat",
            )
            a2 = lib.save_new_asset(
                source_png=src,
                title="Earth",
                prompt="Earth again",
                enhanced_prompt="Earth flat again",
            )
            self.assertNotEqual(a1.id, a2.id)
            self.assertTrue((root / "assets" / f"{a1.id}.png").is_file())
            self.assertTrue((root / "assets" / f"{a2.id}.png").is_file())
            meta = json.loads((root / "metadata" / f"{a1.id}.json").read_text())
            self.assertEqual(meta["title"], "Earth")


if __name__ == "__main__":
    unittest.main()
