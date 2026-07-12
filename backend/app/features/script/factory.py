"""Factory for the default ContentGenerator (Phase 3.5)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.script.generator import PlaceholderContentGenerator
from app.features.script.ollama.generator import OllamaContentGenerator
from app.features.script.protocols import ContentGenerator

logger = get_logger(__name__)


def create_content_generator(settings: Settings) -> ContentGenerator:
    """Prefer Ollama; keep Placeholder in tests or when Ollama is disabled.

    Public HTTP APIs stay the same — only the injected generator changes.
    """
    if settings.is_testing or not settings.ollama_enabled:
        logger.info(
            "Using PlaceholderContentGenerator",
            extra={
                "event": "content_generator_selected",
                "generator": "placeholder",
                "testing": settings.is_testing,
                "ollama_enabled": settings.ollama_enabled,
            },
        )
        return PlaceholderContentGenerator()

    logger.info(
        "Using OllamaContentGenerator",
        extra={
            "event": "content_generator_selected",
            "generator": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    )
    return OllamaContentGenerator.from_settings(settings)
