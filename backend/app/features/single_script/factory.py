"""Factory for SingleScriptGenerator."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.single_script.generator import PlaceholderSingleScriptGenerator
from app.features.single_script.ollama.generator import OllamaSingleScriptGenerator
from app.features.single_script.protocols import SingleScriptGenerator

logger = get_logger(__name__)


def create_single_script_generator(settings: Settings) -> SingleScriptGenerator:
    """Prefer Ollama; keep Placeholder in tests or when Ollama is disabled."""
    if settings.is_testing or not settings.ollama_enabled:
        logger.info(
            "Using PlaceholderSingleScriptGenerator",
            extra={
                "event": "single_script_generator_selected",
                "generator": "placeholder",
                "testing": settings.is_testing,
                "ollama_enabled": settings.ollama_enabled,
            },
        )
        return PlaceholderSingleScriptGenerator()

    logger.info(
        "Using OllamaSingleScriptGenerator",
        extra={
            "event": "single_script_generator_selected",
            "generator": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    )
    return OllamaSingleScriptGenerator.from_settings(settings)
