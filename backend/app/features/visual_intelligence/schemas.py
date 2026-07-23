"""Request/response schemas for the Visual Intelligence HTTP feature."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.visual_intelligence.schemas import SceneInput


class AnalyzeRequest(BaseModel):
    """Classify one or more scenes' visual intent.

    Provide either ``scene`` (single) or ``scenes`` (batch). At least one scene
    is required.
    """

    model_config = ConfigDict(extra="forbid")

    scene: SceneInput | None = None
    scenes: list[SceneInput] = Field(default_factory=list)

    def collected(self) -> list[SceneInput]:
        items = list(self.scenes)
        if self.scene is not None:
            items.insert(0, self.scene)
        return items


class PlanRequest(BaseModel):
    """Plan visuals for a whole EducationalScript or a list of scenes.

    Provide either ``script`` (an EducationalScript-shaped dict with
    ``teaching_sections``) or ``scenes``. When ``include_timeline`` is true the
    response also contains Timeline-Engine-ready scene JSON.
    """

    model_config = ConfigDict(extra="forbid")

    script: dict[str, Any] | None = None
    scenes: list[SceneInput] = Field(default_factory=list)
    include_timeline: bool = True
