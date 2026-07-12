"""SingleScriptGenerator protocol — TeachingOutline → EducationalScript in one pass."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.outline.schemas import TeachingOutline
from app.features.script.schemas import EducationalScript


@runtime_checkable
class SingleScriptGenerator(Protocol):
    """Generate a full EducationalScript from a TeachingOutline in one call."""

    def generate(self, outline: TeachingOutline) -> EducationalScript: ...
