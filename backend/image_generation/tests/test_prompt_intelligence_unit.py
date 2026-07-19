"""Unit tests for Phase 5.6 Prompt Intelligence Engine."""

from __future__ import annotations

import unittest

from image_generation.prompt_enhancer import PromptEnhancer
from image_generation.prompt_intelligence import (
    LLMPromptEngine,
    RuleBasedPromptEngine,
)
from image_generation.prompt_intelligence.prompt_validator import PromptValidator
from image_generation.prompt_intelligence.subject_classifier import SubjectClassifier
from image_generation.prompt_intelligence.style_profiles import get_style


class SubjectClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clf = SubjectClassifier()

    def test_examples(self) -> None:
        expected = {
            "Earth": "Geography",
            "Heart": "Biology",
            "Photosynthesis": "Biology",
            "Computer Motherboard": "Computer Science",
            "Sorting Algorithm": "Computer Science",
            "Newton's Laws": "Physics",
            "Volcano": "Geography",
            "DNA": "Biology",
        }
        for prompt, subject in expected.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(self.clf.classify(prompt).subject, subject)


class PromptEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RuleBasedPromptEngine()

    def test_earth_shape(self) -> None:
        r = self.engine.enhance("Earth")
        self.assertEqual(r.subject, "Geography")
        self.assertEqual(r.template_used, "geography_v1")
        self.assertEqual(r.style_id, "flat_vector")
        self.assertIn("flat vector", r.enhanced_prompt.lower())
        self.assertIn("transparent background", r.enhanced_prompt.lower())
        self.assertIn("no text", r.negative_prompt)
        self.assertTrue(r.validated)
        self.assertGreater(r.confidence, 0.5)

    def test_photosynthesis_diagram(self) -> None:
        r = self.engine.enhance("Photosynthesis")
        self.assertEqual(r.subject, "Biology")
        self.assertIn("photosynthesis", r.enhanced_prompt.lower())
        self.assertIn("chloroplast", r.enhanced_prompt.lower())

    def test_heart_anatomical(self) -> None:
        r = self.engine.enhance("Human Heart")
        self.assertEqual(r.subject, "Biology")
        self.assertIn("heart", r.enhanced_prompt.lower())
        self.assertEqual(r.title, "Human Heart")

    def test_style_override(self) -> None:
        r = self.engine.enhance("Earth", style="minimal_icon")
        self.assertEqual(r.style_id, "minimal_icon")
        self.assertIn("icon", r.enhanced_prompt.lower())

    def test_scores_present(self) -> None:
        r = self.engine.enhance("DNA")
        d = r.scores.to_dict()
        for key in ("clarity", "subject_confidence", "educational_suitability", "complexity"):
            self.assertIn(key, d)
            self.assertGreaterEqual(d[key], 0.0)
            self.assertLessEqual(d[key], 1.0)

    def test_llm_placeholder(self) -> None:
        r = LLMPromptEngine().enhance("Volcano")
        self.assertEqual(r.subject, "Geography")
        self.assertEqual(r.metadata.get("llm_engine"), "placeholder")


class PromptValidatorTests(unittest.TestCase):
    def test_empty(self) -> None:
        v = PromptValidator().validate("  ")
        self.assertFalse(v.ok)
        self.assertIn("missing_subject", v.notes)

    def test_duplicate_words(self) -> None:
        v = PromptValidator().validate("Earth Earth")
        self.assertTrue(v.ok)
        self.assertEqual(v.cleaned_prompt, "Earth")


class StyleProfileTests(unittest.TestCase):
    def test_default(self) -> None:
        self.assertEqual(get_style(None).style_id, "flat_vector")

    def test_alias(self) -> None:
        self.assertEqual(get_style("flat").style_id, "flat_vector")


class PromptEnhancerAdapterTests(unittest.TestCase):
    def test_dict_shape_for_asset_manager(self) -> None:
        out = PromptEnhancer().enhance("Earth")
        for key in ("title", "category", "enhanced_prompt", "style", "original_prompt"):
            self.assertIn(key, out)
        self.assertEqual(out["category"], "Geography")
        self.assertIn("Earth", out["title"])


if __name__ == "__main__":
    unittest.main()
