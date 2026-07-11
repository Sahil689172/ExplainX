"""Health and readiness routes."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Request

from app import __version__
from app.api.deps import request_id_dep, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.core.enums import HealthStatus
from app.db.session import get_engine
from app.shared.envelopes import success_payload
from app.shared.health import DoctorCheck, DoctorData, HealthData

_STARTED_AT = time.monotonic()

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Liveness probe — API process is up."""
    data = HealthData(
        status=HealthStatus.OK.value,
        uptime_sec=round(time.monotonic() - _STARTED_AT, 3),
        version=__version__,
        env=settings.env.value,
    )
    return success_payload(
        data.model_dump(),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/system/doctor")
async def doctor(
    request: Request,
    settings: Settings = Depends(settings_dep),
    _request_id: str = Depends(request_id_dep),
) -> dict[str, Any]:
    """Readiness-oriented checks for Phase 1.1 (filesystem + config only).

    Later phases add Ollama, Piper, FFmpeg, and SQLite schema checks.
    """
    checks: list[DoctorCheck] = []

    data_ok = settings.data_root_path.exists() and settings.data_root_path.is_dir()
    checks.append(
        DoctorCheck(
            id="data_root",
            ok=data_ok,
            detail=str(settings.data_root_path) if data_ok else "data root missing",
        )
    )

    logs_ok = settings.logs_dir.exists()
    checks.append(
        DoctorCheck(
            id="logs_dir",
            ok=logs_ok,
            detail=None if logs_ok else "logs directory missing",
        )
    )

    checks.append(
        DoctorCheck(
            id="sqlite",
            ok=True,
            detail="schema ready (Phase 1.2)",
        )
    )
    try:
        get_engine().connect().close()
    except Exception as exc:  # noqa: BLE001
        checks[-1] = DoctorCheck(id="sqlite", ok=False, detail=str(exc))
    sqlite_ok = checks[-1].ok
    checks.append(DoctorCheck(id="ffmpeg", ok=False, detail="not required in Phase 1.3"))
    checks.append(DoctorCheck(id="ollama", ok=False, detail="not required in Phase 1.3"))
    checks.append(DoctorCheck(id="piper", ok=False, detail="not required in Phase 1.3"))

    foundation_ready = data_ok and logs_ok and sqlite_ok
    payload = DoctorData(ready=foundation_ready, checks=checks)
    return success_payload(
        payload.model_dump(),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
