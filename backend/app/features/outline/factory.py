"""Factory for the default OutlineGenerator (Phase 3.7)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.outline.generator import PlaceholderOutlineGenerator
from app.features.outline.ollama.generator import OllamaOutlineGenerator
from app.features.outline.protocols import OutlineGenerator

logger = get_logger(__name__)


def create_outline_generator(settings: Settings) -> OutlineGenerator:
    """Prefer Ollama; keep Placeholder in tests or when Ollama is disabled."""
    if settings.is_testing or not settings.ollama_enabled:
        logger.info(
            "Using PlaceholderOutlineGenerator",
            extra={
                "event": "outline_generator_selected",
                "generator": "placeholder",
                "testing": settings.is_testing,
                "ollama_enabled": settings.ollama_enabled,
            },
        )
        return PlaceholderOutlineGenerator()

    logger.info(
        "Using OllamaOutlineGenerator",
        extra={
            "event": "outline_generator_selected",
            "generator": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    )
    return OllamaOutlineGenerator.from_settings(settings)
