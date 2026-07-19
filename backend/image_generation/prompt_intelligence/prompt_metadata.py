"""Prompt metadata schemas for Phase 5.6 Prompt Intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PromptScores:
    """Heuristic scores for an enhanced prompt (0–1)."""

    clarity: float = 0.0
    subject_confidence: float = 0.0
    educational_suitability: float = 0.0
    complexity: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class PromptIntelligenceResult:
    """Full output of the Prompt Intelligence Engine."""

    original_prompt: str
    enhanced_prompt: str
    negative_prompt: str
    subject: str
    style: str
    style_id: str
    title: str
    keywords: list[str]
    template_used: str
    confidence: float
    scores: PromptScores = field(default_factory=PromptScores)
    validated: bool = True
    validation_notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_prompt": self.original_prompt,
            "enhanced_prompt": self.enhanced_prompt,
            "negative_prompt": self.negative_prompt,
            "subject": self.subject,
            "style": self.style,
            "style_id": self.style_id,
            "title": self.title,
            "keywords": list(self.keywords),
            "template_used": self.template_used,
            "confidence": self.confidence,
            "scores": self.scores.to_dict(),
            "validated": self.validated,
            "validation_notes": list(self.validation_notes),
            "metadata": dict(self.metadata),
        }
