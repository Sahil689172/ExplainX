"""Validate continuous narration before SceneBuilder."""

from __future__ import annotations

from app.core.errors import ValidationAppError
from app.features.narration.schemas import NarrationDocument
from app.features.script.metrics import count_words

_UNSPEAKABLE = ("```", "<html", "<table")


class NarrationValidator:
    """Lightweight checks on raw narration text."""

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
