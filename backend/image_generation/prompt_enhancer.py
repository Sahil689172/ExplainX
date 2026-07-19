"""Lightweight prompt enhancer for educational illustrations.

Phase 5.6: delegates to :class:`RuleBasedPromptEngine` by default so AssetManager
receives smarter prompts without any Asset Manager code changes.

Swap engines via DI::

    PromptEnhancer(engine=LLMPromptEngine())
"""

from __future__ import annotations

from typing import Any

from image_generation.prompt_intelligence.prompt_engine import (
    PromptEngine,
    RuleBasedPromptEngine,
)


class PromptEnhancer:
    """Adapter: Prompt Intelligence → AssetManager-compatible dict."""

    def __init__(self, engine: PromptEngine | None = None) -> None:
        self._engine: PromptEngine = engine or RuleBasedPromptEngine()

    def enhance(self, prompt: str, *, style: str = "flat_vector") -> dict[str, Any]:
        result = self._engine.enhance(prompt, style=style)
        return {
            "title": result.title,
            "category": result.subject,
            "enhanced_prompt": result.enhanced_prompt,
            "style": result.style_id,
            "original_prompt": result.original_prompt,
            # Extra fields for repository / future callers (AssetManager ignores unknown keys)
            "negative_prompt": result.negative_prompt,
            "keywords": list(result.keywords),
            "subject": result.subject,
            "template_used": result.template_used,
            "confidence": result.confidence,
            "scores": result.scores.to_dict(),
            "validated": result.validated,
        }
