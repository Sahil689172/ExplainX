"""Factory for RepairGenerator (Phase 3.9)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.quality.generator import PlaceholderRepairGenerator
from app.features.quality.ollama.generator import OllamaRepairGenerator
from app.features.quality.protocols import RepairGenerator

logger = get_logger(__name__)


def create_repair_generator(settings: Settings) -> RepairGenerator:
    if settings.is_testing or not settings.ollama_enabled:
        logger.info(
            "Using PlaceholderRepairGenerator",
            extra={
                "event": "repair_generator_selected",
                "generator": "placeholder",
                "testing": settings.is_testing,
                "ollama_enabled": settings.ollama_enabled,
            },
        )
        return PlaceholderRepairGenerator()

    logger.info(
        "Using OllamaRepairGenerator",
        extra={
            "event": "repair_generator_selected",
            "generator": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
    )
    return OllamaRepairGenerator.from_settings(settings)
