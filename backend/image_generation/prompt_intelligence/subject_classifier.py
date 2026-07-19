"""Subject classifier for educational prompts (rule-based, no LLM)."""

from __future__ import annotations

from dataclasses import dataclass

from image_generation.keyword_expand import normalize_token


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    subject: str
    confidence: float
    matched_term: str | None = None


# Longer / more specific phrases first.
_RULES: tuple[tuple[str, str, float], ...] = (
    ("sorting algorithm", "Computer Science", 0.98),
    ("computer motherboard", "Computer Science", 0.97),
    ("motherboard", "Computer Science", 0.95),
    ("algorithm", "Computer Science", 0.9),
    ("newton's laws", "Physics", 0.98),
    ("newtons laws", "Physics", 0.98),
    ("newton", "Physics", 0.85),
    ("photosynthesis", "Biology", 0.97),
    ("human heart", "Biology", 0.97),
    ("heart", "Biology", 0.93),
    ("dna", "Biology", 0.96),
    ("neuron", "Biology", 0.93),
    ("cell", "Biology", 0.88),
    ("chloroplast", "Biology", 0.9),
    ("volcano", "Geography", 0.95),
    ("earth", "Geography", 0.92),
    ("planet", "Geography", 0.85),
    ("globe", "Geography", 0.88),
    ("water cycle", "Geography", 0.95),
    ("solar system", "Astronomy", 0.96),
    ("moon", "Astronomy", 0.9),
    ("sun", "Astronomy", 0.88),
    ("galaxy", "Astronomy", 0.9),
    ("molecule", "Chemistry", 0.92),
    ("atom", "Chemistry", 0.9),
    ("equation", "Mathematics", 0.88),
    ("geometry", "Mathematics", 0.9),
    ("circuit", "Engineering", 0.9),
    ("gear", "Engineering", 0.85),
    ("pyramid", "History", 0.8),
    ("timeline", "History", 0.8),
)


class SubjectClassifier:
    """Classify a short user prompt into an educational subject."""

    def classify(self, prompt: str) -> ClassificationResult:
        # Normalize smart/curly apostrophes so "Newton's" matches rules.
        text = normalize_token(prompt).replace("\u2019", "'").replace("\u2018", "'")
        if not text:
            return ClassificationResult(subject="General", confidence=0.2)

        for term, subject, confidence in _RULES:
            if term in text:
                return ClassificationResult(
                    subject=subject, confidence=confidence, matched_term=term
                )

        # Token fallback
        for term, subject, confidence in _RULES:
            for token in text.split():
                if token == term:
                    return ClassificationResult(
                        subject=subject,
                        confidence=max(0.7, confidence - 0.1),
                        matched_term=term,
                    )

        return ClassificationResult(subject="General", confidence=0.45)
