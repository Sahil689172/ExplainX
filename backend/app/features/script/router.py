"""Content Intelligence HTTP routes — any input → EducationalScript (Phase 3)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, status

from app.api.deps import get_content_intelligence_service, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.features.script.schemas import GenerateScriptRequest
from app.features.script.service import ContentIntelligenceService
from app.shared.envelopes import success_payload

router = APIRouter(prefix="/projects", tags=["content-intelligence"])


@router.post("/{project_id}/script", status_code=status.HTTP_201_CREATED)
async def generate_script(
    project_id: str,
    request: Request,
    payload: Annotated[GenerateScriptRequest | None, Body()] = None,
    service: ContentIntelligenceService = Depends(get_content_intelligence_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Generate one EducationalScript from the project's topic / PDF / script input."""
    body = payload or GenerateScriptRequest()
    script = service.generate_script(
        project_id,
        target_duration=body.target_duration,
        target_duration_sec=body.target_duration_sec,
    )
    return success_payload(
        script.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/{project_id}/script")
async def get_script(
    project_id: str,
    request: Request,
    service: ContentIntelligenceService = Depends(get_content_intelligence_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    script = service.get_script(project_id)
    return success_payload(
        script.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
