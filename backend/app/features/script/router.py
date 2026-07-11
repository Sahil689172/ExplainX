"""Script Generation HTTP routes — RawContent → EducationalScript."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_script_generation_service, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.features.script.service import ScriptGenerationService
from app.shared.envelopes import success_payload

router = APIRouter(prefix="/projects", tags=["script-generation"])


@router.post("/{project_id}/script", status_code=status.HTTP_201_CREATED)
async def generate_script(
    project_id: str,
    request: Request,
    service: ScriptGenerationService = Depends(get_script_generation_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Generate an EducationalScript from the project's RawContent."""
    script = service.generate_script(project_id)
    return success_payload(
        script.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/{project_id}/script")
async def get_script(
    project_id: str,
    request: Request,
    service: ScriptGenerationService = Depends(get_script_generation_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    script = service.get_script(project_id)
    return success_payload(
        script.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
