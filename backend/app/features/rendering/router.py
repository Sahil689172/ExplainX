"""Rendering router — Phase 1.3 stub (no encode/render logic)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.shared.envelopes import success_payload
from app.shared.schemas import PlaceholderResponse

router = APIRouter(prefix="/rendering", tags=["rendering"])


@router.get("/status")
async def rendering_status(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    data = {
        "status": "not_implemented",
        "module": "rendering",
        "message": "Rendering engine is not available in Phase 1.3.",
        "phase": "1.3",
        "next_phase_hint": "Phase 8 — Rendering Engine",
    }
    return success_payload(
        data,
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/jobs")
async def create_render_job(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    payload = PlaceholderResponse(
        module="rendering",
        message="Creating render jobs is not implemented yet.",
        next_phase_hint="Phase 8 — Rendering Engine",
    )
    body = success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)


@router.get("/jobs/{job_id}")
async def get_render_job(
    job_id: str,
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    payload = PlaceholderResponse(
        module="rendering",
        message=f"Render job '{job_id}' is not implemented yet.",
        next_phase_hint="Phase 8 — job progress polling",
    )
    body = success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)
