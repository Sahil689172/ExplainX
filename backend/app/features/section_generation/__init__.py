"""Phase 3.8 Section Generation — TeachingOutline → EducationalScript (per section)."""

from app.features.section_generation.schemas import SectionOutput
from app.features.section_generation.service import SectionGenerationService

__all__ = [
    "SectionOutput",
    "SectionGenerationService",
]
