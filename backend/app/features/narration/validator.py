"""Validate continuous English narration before SceneBuilder."""

from __future__ import annotations

import re

from app.core.errors import ValidationAppError
from app.features.narration.languages import CANONICAL_SCRIPT_LANGUAGE
from app.features.narration.schemas import NarrationDocument
from app.features.script.metrics import count_words

_UNSPEAKABLE = ("```", "<html", "<table")
_HEADING_LINE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+\S")
_BULLET_LINE = re.compile(r"(?m)^\s*[-*•]\s+\S")
_JSONISH = re.compile(r"^\s*[\{\[]")


class NarrationValidator:
    """Lightweight checks on raw English narration text."""

    def __init__(self, *, min_words: int = 40) -> None:
        self._min_words = min_words

    def validate(self, narration: NarrationDocument) -> None:
        text = narration.text.strip()
        if not text:
            raise ValidationAppError(
                "Narration text is empty.",
                code="NARRATION_VALIDATION_ERROR",
                details={"field": "text"},
            )

        lang = (narration.language or CANONICAL_SCRIPT_LANGUAGE).strip().lower()[:2]
        if lang != CANONICAL_SCRIPT_LANGUAGE:
            raise ValidationAppError(
                f"Narration language must be English (en); got {narration.language!r}.",
                code="NARRATION_VALIDATION_ERROR",
                details={"language": narration.language},
            )

        words = count_words(text)
        if words < self._min_words:
            raise ValidationAppError(
                f"Narration has only {words} words (minimum {self._min_words}).",
                code="NARRATION_VALIDATION_ERROR",
                details={"word_count": words, "min_words": self._min_words},
            )

        lowered = text.lower()
        for marker in _UNSPEAKABLE:
            if marker in lowered:
                raise ValidationAppError(
                    f"Narration contains unspeakable content ({marker}).",
                    code="NARRATION_VALIDATION_ERROR",
                    details={"marker": marker},
                )

        if _JSONISH.match(text) and ('"narration"' in text or '"sections"' in text):
            raise ValidationAppError(
                "Narration looks like JSON; expected plain spoken text.",
                code="NARRATION_VALIDATION_ERROR",
                details={"reason": "json"},
            )

        if _HEADING_LINE.search(text):
            raise ValidationAppError(
                "Narration contains markdown headings.",
                code="NARRATION_VALIDATION_ERROR",
                details={"reason": "heading"},
            )

        if _BULLET_LINE.search(text):
            raise ValidationAppError(
                "Narration contains bullet lists.",
                code="NARRATION_VALIDATION_ERROR",
                details={"reason": "bullets"},
            )
