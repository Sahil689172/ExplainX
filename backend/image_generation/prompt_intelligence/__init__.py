"""Phase 5.6 — Prompt Intelligence Engine.

Transforms short user prompts into high-quality educational generation prompts
before Asset Manager / cache / OpenVINO.

Public API
----------
- ``PromptEngine`` — abstract interface
- ``RuleBasedPromptEngine`` — default implementation
- ``LLMPromptEngine`` — future LLM placeholder
- ``PromptIntelligenceResult`` — structured metadata
"""

from image_generation.prompt_intelligence.prompt_engine import (
    LLMPromptEngine,
    PromptEngine,
    PromptOptimizer,
    PromptScorer,
    RuleBasedPromptEngine,
)
from image_generation.prompt_intelligence.prompt_metadata import (
    PromptIntelligenceResult,
    PromptScores,
)
from image_generation.prompt_intelligence.subject_classifier import (
    ClassificationResult,
    SubjectClassifier,
)
from image_generation.prompt_intelligence.style_profiles import (
    DEFAULT_STYLE_ID,
    STYLE_PROFILES,
    StyleProfile,
    get_style,
)

__all__ = [
    "ClassificationResult",
    "DEFAULT_STYLE_ID",
    "LLMPromptEngine",
    "PromptEngine",
    "PromptIntelligenceResult",
    "PromptOptimizer",
    "PromptScores",
    "PromptScorer",
    "RuleBasedPromptEngine",
    "STYLE_PROFILES",
    "StyleProfile",
    "SubjectClassifier",
    "get_style",
]
