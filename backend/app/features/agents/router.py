"""Agents router — Phase 1.3 stub (no agent execution)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.shared.envelopes import success_payload
from app.shared.schemas import PlaceholderResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Return the planned agent catalog without executing anything."""
    data = {
        "status": "not_implemented",
        "module": "agents",
        "message": "Agent execution is not available in Phase 1.3.",
        "planned_agents": [
            "parser_agent",
            "cleaning_agent",
            "knowledge_agent",
            "script_agent",
            "scene_planner_agent",
            "visual_planning_agent",
            "voice_agent",
            "rendering_agent",
        ],
        "phase": "1.3",
        "next_phase_hint": "Phase 2+ agent pipeline",
    }
    return success_payload(
        data,
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/run")
async def run_agents(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    payload = PlaceholderResponse(
        module="agents",
        message="Starting agent pipelines is not implemented yet.",
        next_phase_hint="Phase 2+ — LangGraph orchestration",
    )
    body = success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)


@router.get("/{agent_name}/status")
async def agent_status(
    agent_name: str,
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    payload = PlaceholderResponse(
        module="agents",
        message=f"Status for agent '{agent_name}' is not implemented yet.",
        next_phase_hint="Phase 2+ — agent job tracking",
    )
    body = success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)
