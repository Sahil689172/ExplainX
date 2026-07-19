"""Negative prompt builder for educational assets."""

from __future__ import annotations

NEGATIVE_TERMS: tuple[str, ...] = (
    "no text",
    "no labels",
    "no words",
    "no letters",
    "no numbers",
    "no watermark",
    "no logo",
    "no signature",
    "no blurry image",
    "no extra objects",
    "no background clutter",
    "no cropped object",
    "no duplicate objects",
    "no border",
    "no frame",
)


class NegativePromptBuilder:
    """Always-on negative prompt for ExplainX educational generations."""

    def build(self) -> str:
        return ", ".join(NEGATIVE_TERMS)

    def as_positive_suffix(self) -> str:
        """Examples bake constraints into the positive prompt string as well."""
        return ", ".join(NEGATIVE_TERMS)
