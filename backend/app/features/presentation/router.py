"""Presentation plan HTTP routes — RawContent → PresentationPlan (Phase 2.3)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_presentation_plan_service, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.features.presentation.service import PresentationPlanService
from app.shared.envelopes import success_payload

router = APIRouter(prefix="/projects", tags=["presentation-plan"])


@router.post(
    "/{project_id}/presentation-plan",
    status_code=status.HTTP_201_CREATED,
)
async def generate_presentation_plan(
    project_id: str,
    request: Request,
    service: PresentationPlanService = Depends(get_presentation_plan_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Generate a PresentationPlan from the project's RawContent (placeholder planner)."""
    plan = service.generate_plan(project_id)
    return success_payload(
        plan.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/{project_id}/presentation-plan")
async def get_presentation_plan(
    project_id: str,
    request: Request,
    service: PresentationPlanService = Depends(get_presentation_plan_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    plan = service.get_plan(project_id)
    return success_payload(
        plan.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
