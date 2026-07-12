"""Single-pass script generation — TeachingOutline → EducationalScript (one LLM call)."""

from app.features.single_script.protocols import SingleScriptGenerator
from app.features.single_script.service import SingleScriptGenerationService

__all__ = [
    "SingleScriptGenerator",
    "SingleScriptGenerationService",
]
