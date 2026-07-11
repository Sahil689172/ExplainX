"""Documents listing stub — uploads live under ``/projects/{id}/documents``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.models.api.envelopes import success_payload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents_hint(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    """Phase 2.1/2.2: document ingest is project-scoped."""
    return success_payload(
        {
            "status": "project_scoped",
            "module": "documents",
            "message": (
                "Upload via POST /api/v1/projects/{project_id}/documents. "
                "Topic via PUT .../source/topic. Script via PUT .../source/script."
            ),
            "phase": "2.1-2.2",
        },
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
