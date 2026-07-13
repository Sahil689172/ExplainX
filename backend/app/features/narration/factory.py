"""Factory for NarrationGenerator."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.narration.generator import PlaceholderNarrationGenerator
from app.features.narration.ollama_generator import OllamaNarrationGenerator
from app.features.narration.protocols import NarrationGenerator

logger = get_logger(__name__)


def create_narration_generator(settings: Settings) -> NarrationGenerator:
    if settings.is_testing or not settings.ollama_enabled:
        logger.info(
            "Using PlaceholderNarrationGenerator",
            extra={
                "event": "narration_generator_selected",
                "generator": "placeholder",
                "testing": settings.is_testing,
                "ollama_enabled": settings.ollama_enabled,
            },
        )
        return PlaceholderNarrationGenerator()

    logger.info(
        "Using OllamaNarrationGenerator",
        extra={
            "event": "narration_generator_selected",
            "generator": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    )
    return OllamaNarrationGenerator.from_settings(settings)
