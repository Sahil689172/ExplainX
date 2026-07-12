"""Factory for SectionGenerator (Phase 3.8)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.section_generation.generator import PlaceholderSectionGenerator
from app.features.section_generation.ollama.generator import OllamaSectionGenerator
from app.features.section_generation.protocols import SectionGenerator

logger = get_logger(__name__)


def create_section_generator(settings: Settings) -> SectionGenerator:
    """Prefer Ollama; keep Placeholder in tests or when Ollama is disabled."""
    if settings.is_testing or not settings.ollama_enabled:
        logger.info(
            "Using PlaceholderSectionGenerator",
            extra={
                "event": "section_generator_selected",
                "generator": "placeholder",
                "testing": settings.is_testing,
                "ollama_enabled": settings.ollama_enabled,
            },
        )
        return PlaceholderSectionGenerator()

    logger.info(
        "Using OllamaSectionGenerator",
        extra={
            "event": "section_generator_selected",
            "generator": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    )
    return OllamaSectionGenerator.from_settings(settings)
