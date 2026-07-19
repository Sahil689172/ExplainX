"""Prompt Intelligence Engine — rule-based now, LLM-swappable later.

Architecture
------------
User Prompt → PromptEngine.enhance() → PromptIntelligenceResult
                                      → AssetManager (via PromptEnhancer adapter)

Implementations
---------------
- ``PromptEngine`` — abstract interface
- ``RuleBasedPromptEngine`` — templates + classifier (Phase 5.6)
- ``LLMPromptEngine`` — placeholder for future LLM rewriting
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from image_generation.keyword_expand import expand_from_prompt, normalize_token
from image_generation.logger import get_engine_logger
from image_generation.prompt_intelligence.negative_prompt_builder import (
    NegativePromptBuilder,
)
from image_generation.prompt_intelligence.prompt_metadata import (
    PromptIntelligenceResult,
    PromptScores,
)
from image_generation.prompt_intelligence.prompt_templates import (
    SUBJECT_EXTRAS,
    UNIVERSAL_POSITIVE_RULES,
    get_template,
)
from image_generation.prompt_intelligence.prompt_validator import PromptValidator
from image_generation.prompt_intelligence.style_profiles import (
    DEFAULT_STYLE_ID,
    get_style,
)
from image_generation.prompt_intelligence.subject_classifier import SubjectClassifier


# Common educational abbreviations → expanded phrases
_ABBREVIATIONS: dict[str, str] = {
    "dna": "DNA",
    "rna": "RNA",
    "cpu": "CPU",
    "gpu": "GPU",
    "pcb": "printed circuit board",
    "ai": "artificial intelligence",
    "ml": "machine learning",
}


class PromptOptimizer:
    """Normalize capitalization, expand abbreviations, remove duplicate adjectives."""

    def optimize_subject_phrase(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return cleaned

        tokens = cleaned.split()
        out: list[str] = []
        for tok in tokens:
            key = tok.lower().strip(".,;:")
            if key in _ABBREVIATIONS:
                # Keep acronym casing where appropriate
                expanded = _ABBREVIATIONS[key]
                if expanded.isupper() and len(expanded) <= 4:
                    out.append(expanded)
                else:
                    out.append(expanded)
            else:
                out.append(tok)

        # Deduplicate consecutive adjectives / words (case-insensitive)
        deduped: list[str] = []
        for tok in out:
            if not deduped or deduped[-1].lower() != tok.lower():
                deduped.append(tok)

        phrase = " ".join(deduped)
        # Title-case short subject phrases unless already acronym-heavy
        if phrase.isupper() and len(phrase) <= 4:
            return phrase
        if phrase.lower() == "dna":
            return "DNA"
        # Preserve intentional capitalization for possessives like Newton's
        if "'" in phrase or "’" in phrase:
            return phrase[0].upper() + phrase[1:] if phrase else phrase
        return phrase.title() if len(phrase.split()) <= 4 else phrase

    def dedupe_clauses(self, clauses: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for clause in clauses:
            key = normalize_token(clause)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(clause.strip())
        return out


class PromptScorer:
    """Heuristic prompt quality scores (0–1)."""

    def score(
        self,
        *,
        original: str,
        enhanced: str,
        subject_confidence: float,
        subject: str,
    ) -> PromptScores:
        orig_tokens = len(original.split())
        clarity = min(1.0, 0.4 + 0.15 * min(orig_tokens, 4))
        if orig_tokens == 1:
            clarity = 0.75  # short but specific subjects are fine for educa
        educational = 0.55
        enh_l = enhanced.lower()
        for needle in (
            "educational",
            "textbook",
            "illustration",
            "flat vector",
            "transparent",
        ):
            if needle in enh_l:
                educational += 0.08
        educational = min(1.0, educational)
        if subject != "General":
            educational = min(1.0, educational + 0.05)

        complexity = min(1.0, len(enhanced.split()) / 40.0)
        return PromptScores(
            clarity=round(clarity, 3),
            subject_confidence=round(subject_confidence, 3),
            educational_suitability=round(educational, 3),
            complexity=round(complexity, 3),
        )


class PromptEngine(ABC):
    """Future-compatible interface for prompt rewriting."""

    @abstractmethod
    def enhance(
        self,
        prompt: str,
        *,
        style: str | None = None,
        **kwargs: Any,
    ) -> PromptIntelligenceResult:
        """Transform a raw user prompt into an educational generation prompt."""


class RuleBasedPromptEngine(PromptEngine):
    """Template + classifier engine (no LLM)."""

    def __init__(
        self,
        *,
        classifier: SubjectClassifier | None = None,
        validator: PromptValidator | None = None,
        negative_builder: NegativePromptBuilder | None = None,
        optimizer: PromptOptimizer | None = None,
        scorer: PromptScorer | None = None,
        logger: Any | None = None,
    ) -> None:
        self._classifier = classifier or SubjectClassifier()
        self._validator = validator or PromptValidator()
        self._negatives = negative_builder or NegativePromptBuilder()
        self._optimizer = optimizer or PromptOptimizer()
        self._scorer = scorer or PromptScorer()
        self._log = logger or get_engine_logger("image_generation.prompt_intelligence")

    def enhance(
        self,
        prompt: str,
        *,
        style: str | None = None,
        **kwargs: Any,
    ) -> PromptIntelligenceResult:
        style_id = style or DEFAULT_STYLE_ID
        self._log.info("PROMPT_RECEIVED prompt=%r style=%s", prompt, style_id)

        validation = self._validator.validate(prompt)
        self._log.info(
            "PROMPT_VALIDATED ok=%s notes=%s",
            validation.ok,
            ",".join(validation.notes) or "-",
        )
        if not validation.ok:
            # Soft-fail: still produce a General prompt from whatever text we have
            subject_text = validation.cleaned_prompt or "educational concept"
            classification = self._classifier.classify(subject_text)
            style_profile = get_style(style_id)
            negative = self._negatives.build()
            fallback = (
                f"A clean flat vector educational illustration of {subject_text}, "
                f"{style_profile.prompt_clause}, centered composition, isolated object, "
                f"transparent background, {self._negatives.as_positive_suffix()}"
            )
            scores = self._scorer.score(
                original=prompt or "",
                enhanced=fallback,
                subject_confidence=classification.confidence * 0.5,
                subject=classification.subject,
            )
            return PromptIntelligenceResult(
                original_prompt=prompt or "",
                enhanced_prompt=fallback,
                negative_prompt=negative,
                subject=classification.subject,
                style=style_profile.display_name,
                style_id=style_profile.style_id,
                title=self._title_from(subject_text),
                keywords=expand_from_prompt(subject_text),
                template_used="fallback_v1",
                confidence=classification.confidence * 0.5,
                scores=scores,
                validated=False,
                validation_notes=validation.notes,
            )

        subject_text = validation.cleaned_prompt
        classification = self._classifier.classify(subject_text)
        self._log.info(
            "SUBJECT_CLASSIFIED subject=%s confidence=%.2f matched=%s",
            classification.subject,
            classification.confidence,
            classification.matched_term or "-",
        )

        style_profile = get_style(style_id)
        self._log.info(
            "STYLE_SELECTED style_id=%s name=%s",
            style_profile.style_id,
            style_profile.display_name,
        )

        template = get_template(classification.subject)
        display_subject = self._optimizer.optimize_subject_phrase(subject_text)
        title = self._title_from(display_subject)

        # Build positive prompt clauses
        lower = normalize_token(subject_text)
        extras = SUBJECT_EXTRAS.get(lower)
        clauses: list[str] = []

        if extras and classification.subject == "Biology" and "photosynthesis" in lower:
            clauses.append(
                f"A clean educational diagram {extras}, "
                f"{style_profile.prompt_clause}"
            )
        elif extras and "heart" in lower:
            clauses.append(
                f"A flat vector {extras}, "
                f"isolated object, transparent background, "
                f"educational biology textbook style, clean outlines, high quality"
            )
        else:
            clauses.append(
                template.lead_in.format(subject=display_subject)
            )
            if extras:
                clauses.append(extras)
            clauses.append(template.subject_hints)
            clauses.append(style_profile.prompt_clause)

        clauses.extend(UNIVERSAL_POSITIVE_RULES)
        # Bake a subset of negatives into the positive string (per Phase 5.6 examples)
        positive_neg_subset = (
            "no text",
            "no labels",
            "no watermark",
            "no logo",
            "no signature",
        )
        clauses.extend(positive_neg_subset)

        clauses = self._optimizer.dedupe_clauses(clauses)
        enhanced = ", ".join(clauses)
        # Grammar / polish: collapse duplicate commas / spaces
        enhanced = re.sub(r"\s*,\s*,+", ", ", enhanced)
        enhanced = re.sub(r"\s+", " ", enhanced).strip(" ,")

        negative = self._negatives.build()
        self._log.info("NEGATIVE_PROMPT_CREATED length=%s", len(negative))

        keywords = expand_from_prompt(
            f"{subject_text} {display_subject} {classification.subject}",
            title=title,
        )
        # Include subject for repository search compatibility
        if classification.subject.lower() not in {normalize_token(k) for k in keywords}:
            keywords = sorted(set(keywords) | {normalize_token(classification.subject)})

        scores = self._scorer.score(
            original=subject_text,
            enhanced=enhanced,
            subject_confidence=classification.confidence,
            subject=classification.subject,
        )
        confidence = round(
            0.6 * classification.confidence + 0.4 * scores.educational_suitability,
            3,
        )

        self._log.info(
            "PROMPT_ENHANCED subject=%s template=%s confidence=%.3f",
            classification.subject,
            template.template_id,
            confidence,
        )

        return PromptIntelligenceResult(
            original_prompt=subject_text,
            enhanced_prompt=enhanced,
            negative_prompt=negative,
            subject=classification.subject,
            style=style_profile.display_name,
            style_id=style_profile.style_id,
            title=title,
            keywords=keywords,
            template_used=template.template_id,
            confidence=confidence,
            scores=scores,
            validated=True,
            validation_notes=validation.notes,
            metadata={"matched_term": classification.matched_term},
        )

    def _title_from(self, subject_text: str) -> str:
        lower = normalize_token(subject_text)
        known = {
            "dna": "DNA",
            "rna": "RNA",
            "human heart": "Human Heart",
            "planet earth": "Earth",
            "earth": "Earth",
            "newton's laws": "Newton's Laws",
            "newtons laws": "Newton's Laws",
            "computer motherboard": "Computer Motherboard",
            "sorting algorithm": "Sorting Algorithm",
            "photosynthesis": "Photosynthesis",
            "volcano": "Volcano",
            "heart": "Heart",
        }
        if lower in known:
            return known[lower]
        for phrase, title in known.items():
            if phrase in lower:
                return title
        optimized = self._optimizer.optimize_subject_phrase(subject_text)
        return optimized or "Asset"


class LLMPromptEngine(PromptEngine):
    """Placeholder for future LLM-based prompt rewriting.

    Swap this in via dependency injection without changing AssetManager:

        AssetManager(generation_service=..., enhancer=PromptEnhancer(engine=LLMPromptEngine(...)))
    """

    def __init__(self, *, model_id: str | None = None) -> None:
        self.model_id = model_id or "future-llm"
        self._fallback = RuleBasedPromptEngine()

    def enhance(
        self,
        prompt: str,
        *,
        style: str | None = None,
        **kwargs: Any,
    ) -> PromptIntelligenceResult:
        # Not implemented yet — safe fallback to rules so callers never break.
        result = self._fallback.enhance(prompt, style=style, **kwargs)
        result.metadata["llm_engine"] = "placeholder"
        result.metadata["model_id"] = self.model_id
        return result
