"""Lightweight prompt enhancer for educational illustrations (no LLM)."""

from __future__ import annotations

import re

from image_generation.keyword_expand import normalize_token


_TITLE_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "with",
        "and",
        "for",
        "showing",
        "show",
        "illustration",
        "illustrations",
        "diagram",
        "diagrams",
        "educational",
        "flat",
        "vector",
        "clean",
        "minimal",
        "textbook",
        "infographic",
        "icon",
        "style",
        "labeled",
        "label",
        "cross",
        "section",
    }
)

_CATEGORY_HINTS: tuple[tuple[str, str], ...] = (
    ("heart", "Biology"),
    ("dna", "Biology"),
    ("photosynthesis", "Biology"),
    ("cell", "Biology"),
    ("neuron", "Biology"),
    ("earth", "Geography"),
    ("planet", "Geography"),
    ("volcano", "Geography"),
    ("solar", "Astronomy"),
    ("moon", "Astronomy"),
    ("water cycle", "Earth Science"),
    ("motherboard", "Technology"),
)


class PromptEnhancer:
    """Derive title, category, and an enhanced prompt string for caching / generation."""

    def enhance(self, prompt: str, *, style: str = "flat_vector") -> dict[str, str]:
        cleaned = " ".join(prompt.strip().split())
        title = self._extract_title(cleaned)
        category = self._guess_category(cleaned, title)
        enhanced = (
            f"{cleaned}, {style.replace('_', ' ')} educational illustration, "
            "clear silhouette, transparent background, high contrast, centered subject"
        )
        return {
            "title": title,
            "category": category,
            "enhanced_prompt": enhanced,
            "style": style,
            "original_prompt": cleaned,
        }

    def _extract_title(self, prompt: str) -> str:
        lower = normalize_token(prompt)
        # Prefer known multi-word concepts
        for phrase in (
            "solar system",
            "water cycle",
            "human heart",
            "planet earth",
            "blue planet",
            "computer motherboard",
            "volcano cross section",
        ):
            if phrase in lower:
                return phrase.title() if phrase != "dna" else "DNA"

        tokens = re.findall(r"[A-Za-z0-9]+", prompt)
        meaningful = [t for t in tokens if t.lower() not in _TITLE_STOP]
        if not meaningful:
            return "Asset"
        # Take up to 3 content words
        title = " ".join(meaningful[:3])
        if title.lower() == "dna":
            return "DNA"
        return title.title()

    def _guess_category(self, prompt: str, title: str) -> str:
        blob = f"{prompt} {title}".lower()
        for needle, category in _CATEGORY_HINTS:
            if needle in blob:
                return category
        return "General"
