"""Visual Intelligence HTTP routes — analyze / plan / health.

Additive surface: no image generation, no LLM calls, no changes to the Script,
Timeline, or Rendering engines.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_visual_intelligence_service, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.features.visual_intelligence.schemas import AnalyzeRequest, PlanRequest
from app.features.visual_intelligence.service import VisualIntelligenceAppService
from app.shared.envelopes import success_payload

router = APIRouter(prefix="/visual-intelligence", tags=["visual-intelligence"])


@router.post("/analyze")
async def analyze_scenes(
    payload: AnalyzeRequest,
    request: Request,
    service: VisualIntelligenceAppService = Depends(get_visual_intelligence_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Classify visual intent for one or more scenes (rule-based, no LLM)."""
    data = {"intents": service.analyze(payload.collected())}
    return success_payload(
        data,
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/plan")
async def plan_visuals(
    payload: PlanRequest,
    request: Request,
    service: VisualIntelligenceAppService = Depends(get_visual_intelligence_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Produce ScenePlans (and Timeline-ready scene JSON) for a script/scenes."""
    data = service.plan(
        script=payload.script,
        scenes=payload.scenes,
        include_timeline=payload.include_timeline,
    )
    return success_payload(
        data,
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/health")
async def visual_intelligence_health(
    request: Request,
    service: VisualIntelligenceAppService = Depends(get_visual_intelligence_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Report renderer registry status (no LLM, no image generation)."""
    return success_payload(
        service.health(),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
