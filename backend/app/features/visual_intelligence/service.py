"""App-facing orchestration for the Visual Intelligence feature.

Wraps the additive :class:`VisualIntelligenceService` and turns its outputs
into JSON-ready payloads for the HTTP layer. This is the orchestration seam
that connects Script Generation → Visual Intelligence → ScenePlan → Timeline
Engine input, while raw-script consumers keep working unchanged.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import ValidationAppError
from app.core.logging import get_logger
from app.services.visual_intelligence import (
    VisualIntelligenceService,
    scene_plans_to_timeline_scenes,
)
from app.services.visual_intelligence.service import ScenePlan

logger = get_logger(__name__)


class VisualIntelligenceAppService:
    """Thin façade the router depends on (dependency inversion)."""

    def __init__(self, service: VisualIntelligenceService | None = None) -> None:
        self._service = service or VisualIntelligenceService()

    # ---- analyze --------------------------------------------------------- #

    def analyze(self, scenes: list[Any]) -> list[dict[str, Any]]:
        if not scenes:
            raise ValidationAppError(
                "Provide 'scene' or a non-empty 'scenes' list.",
                code="VALIDATION_ERROR",
                details={"field": "scenes"},
            )
        intents = [self._service.analyze(scene) for scene in scenes]
        return [intent.model_dump(mode="json") for intent in intents]

    # ---- plan ------------------------------------------------------------ #

    def plan(
        self,
        *,
        script: dict[str, Any] | None,
        scenes: list[Any],
        include_timeline: bool,
    ) -> dict[str, Any]:
        plans: list[ScenePlan]
        if script is not None:
            plans = self._service.plan_script(script)
            source = "script"
        elif scenes:
            plans = self._service.plan_scenes(scenes)
            source = "scenes"
        else:
            raise ValidationAppError(
                "Provide either 'script' or a non-empty 'scenes' list.",
                code="VALIDATION_ERROR",
                details={"fields": ["script", "scenes"]},
            )

        logger.info(
            "Visual plan generated",
            extra={
                "event": "visual_intelligence_plan_generated",
                "component": "visual_intelligence",
                "source": source,
                "scene_count": len(plans),
            },
        )

        payload: dict[str, Any] = {
            "source": source,
            "scene_count": len(plans),
            "scene_plans": [plan.to_dict() for plan in plans],
        }
        if include_timeline:
            payload["timeline_scenes"] = scene_plans_to_timeline_scenes(plans)
        return payload

    # ---- health ---------------------------------------------------------- #

    def health(self) -> dict[str, Any]:
        renderers = self._service.describe_renderers()
        return {
            "status": "ok",
            "service": "visual_intelligence",
            "llm_enabled": False,
            "image_generation": False,
            "renderer_count": len(renderers),
            "renderers": renderers,
        }
