"""Documents router — Phase 1.3 stub (no upload/parse business logic)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.models.api.common import PlaceholderResponse
from app.models.api.envelopes import success_payload

router = APIRouter(prefix="/documents", tags=["documents"])


def _stub(module: str, message: str, hint: str) -> PlaceholderResponse:
    return PlaceholderResponse(
        module=module,
        message=message,
        next_phase_hint=hint,
    )


@router.get("")
async def list_documents(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    payload = _stub(
        "documents",
        "Document listing is not implemented yet.",
        "Phase 2 — Document Intelligence",
    )
    return success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("")
async def upload_document(
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    payload = _stub(
        "documents",
        "Document upload is not implemented yet.",
        "Phase 2 — Document Intelligence",
    )
    body = success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    request: Request,
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    payload = _stub(
        "documents",
        f"Document '{document_id}' retrieval is not implemented yet.",
        "Phase 2 — Document Intelligence",
    )
    body = success_payload(
        payload.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body)
