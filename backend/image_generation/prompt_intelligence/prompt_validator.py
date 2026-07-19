"""Prompt validation and light repair for educational prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from image_generation.keyword_expand import normalize_token


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    cleaned_prompt: str
    notes: list[str] = field(default_factory=list)
    improved: bool = False


class PromptValidator:
    """Reject or improve prompts that are too short, ambiguous, or empty."""

    MIN_LEN = 2

    def validate(self, prompt: str) -> ValidationResult:
        notes: list[str] = []
        raw = prompt or ""
        cleaned = " ".join(raw.strip().split())
        improved = False

        if not cleaned:
            notes.append("missing_subject")
            return ValidationResult(ok=False, cleaned_prompt="", notes=notes)

        if len(cleaned) < self.MIN_LEN:
            notes.append("too_short")
            return ValidationResult(ok=False, cleaned_prompt=cleaned, notes=notes)

        # Remove duplicate consecutive words
        tokens = cleaned.split()
        deduped: list[str] = []
        for tok in tokens:
            if not deduped or deduped[-1].lower() != tok.lower():
                deduped.append(tok)
            else:
                improved = True
                notes.append("removed_duplicate_word")
        cleaned = " ".join(deduped)

        # Ambiguous single filler words
        if normalize_token(cleaned) in {"thing", "stuff", "object", "item", "this", "that"}:
            notes.append("ambiguous")
            return ValidationResult(ok=False, cleaned_prompt=cleaned, notes=notes)

        # Strip trailing punctuation noise
        new_cleaned = cleaned.strip(" .,;:!")
        if new_cleaned != cleaned:
            cleaned = new_cleaned
            improved = True
            notes.append("normalized_punctuation")

        # Must contain at least one alphanumeric token
        if not re.search(r"[A-Za-z0-9]", cleaned):
            notes.append("missing_subject")
            return ValidationResult(ok=False, cleaned_prompt=cleaned, notes=notes)

        return ValidationResult(
            ok=True, cleaned_prompt=cleaned, notes=notes, improved=improved
        )
