"""Narration feature — continuous spoken lesson text."""

from app.features.narration.schemas import NarrationDocument
from app.features.narration.service import NarrationGenerationService

__all__ = ["NarrationDocument", "NarrationGenerationService"]
