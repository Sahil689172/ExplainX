"""Settings router — read-only foundation exposure (no secrets)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.shared.envelopes import success_payload
from app.shared.schemas import PlaceholderResponse

router = APIRouter(prefix="/settings", tags=["settings"])


class AppSettingsPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_name: str
    env: str
    api_version: str
    debug: bool
    host: str
    port: int
    cors_origins: list[str]
    max_concurrent_jobs: int
    log_level: str
    data_root: str


class SettingsUpdateStub(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Accepted for schema documentation only in Phase 1.3
    note: str | None = Field(default=None, max_length=200)


@router.get("")
async def get_settings_public(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    data = AppSettingsPublic(
        app_name=settings.app_name,
        env=settings.env.value,
        api_version=settings.api_version,
        debug=settings.debug,
        host=settings.host,
        port=settings.port,
        cors_origins=settings.cors_origin_list,
        max_concurrent_jobs=settings.max_concurrent_jobs,
        log_level=settings.log_level,
        data_root=str(settings.data_root_path),
    )
    return success_payload(
        data.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.patch("")
async def update_settings_stub(
    payload: SettingsUpdateStub,
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    stub = PlaceholderResponse(
        module="settings",
        message="Updating app settings via API is not implemented yet.",
        next_phase_hint="Later hardening — persist settings in SQLite",
    )
    body = success_payload(
        {**stub.model_dump(mode="json"), "received": payload.model_dump(mode="json")},
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)
