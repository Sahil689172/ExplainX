"""System information endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app import __version__
from app.api.deps import settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.shared.envelopes import success_payload
from app.shared.schemas import ModuleStatusItem, SystemInfoData

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info")
async def system_info(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Return runtime/system information for the local control plane."""
    data = SystemInfoData(
        app_name=settings.app_name,
        version=__version__,
        api_version=settings.api_version,
        env=settings.env.value,
        debug=settings.debug,
        host=settings.host,
        port=settings.port,
        data_root=str(settings.data_root_path),
        docs_enabled=bool(settings.debug or settings.is_testing),
        features={
            "projects": True,
            "documents": True,
            "input_intelligence": True,
            "content_intelligence": True,
            "script_generation": True,
            "agents": False,
            "rendering": False,
            "settings_api": True,
        },
    )
    return success_payload(
        data.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/modules")
async def system_modules(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """List module readiness for the API surface."""
    modules = [
        ModuleStatusItem(
            name="projects",
            status="ready",
            available=True,
            detail="Phase 1.2 project lifecycle",
        ),
        ModuleStatusItem(
            name="documents",
            status="ready",
            available=True,
            detail="Phase 2.1/2.2 Input Intelligence (topic, PDF, script → RawContent)",
        ),
        ModuleStatusItem(
            name="input_intelligence",
            status="ready",
            available=True,
            detail="InputService + InputRouter + Topic/PDF/Script processors",
        ),
        ModuleStatusItem(
            name="content_intelligence",
            status="ready",
            available=True,
            detail=(
                "Phase 3.5 EducationalScript via processors + "
                "OllamaContentGenerator (Placeholder in tests)"
            ),
        ),
        ModuleStatusItem(
            name="presentation_plan",
            status="placeholder",
            available=True,
            detail="Phase 2.3 PresentationPlan schema + placeholder planner (no LLM)",
        ),
        ModuleStatusItem(
            name="script_generation",
            status="placeholder",
            available=True,
            detail="EducationalScript endpoints (Phase 3.5 Ollama / Placeholder)",
        ),
        ModuleStatusItem(
            name="agents",
            status="stub",
            available=False,
            detail="Placeholder — multi-agent pipeline later",
        ),
        ModuleStatusItem(
            name="rendering",
            status="stub",
            available=False,
            detail="Placeholder — render engine later",
        ),
        ModuleStatusItem(
            name="settings",
            status="ready",
            available=True,
            detail="Read-only app settings exposure",
        ),
    ]
    return success_payload(
        {"items": [m.model_dump(mode="json") for m in modules]},
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
