"""Input Intelligence HTTP routes — topic, PDF, custom script → RawContent."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status

from app.api.deps import get_input_service, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.models.api.envelopes import success_payload
from app.models.api.inputs import ScriptSourceRequest, TopicSourceRequest
from app.services.input.input_service import InputService

router = APIRouter(prefix="/projects", tags=["inputs"])


@router.put("/{project_id}/source/topic")
async def set_topic_source(
    project_id: str,
    payload: TopicSourceRequest,
    request: Request,
    service: InputService = Depends(get_input_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    raw = service.ingest_topic(project_id, payload)
    return success_payload(
        {
            "project_id": project_id,
            "source_type": "topic",
            "source_path": raw.source_path,
            "source_hash": raw.source_hash,
            "topic": payload.topic,
            "raw_content": raw.model_dump(mode="json"),
        },
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.put("/{project_id}/source/script")
async def set_script_source(
    project_id: str,
    payload: ScriptSourceRequest,
    request: Request,
    service: InputService = Depends(get_input_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    raw = service.ingest_script(project_id, payload)
    return success_payload(
        {
            "project_id": project_id,
            "source_type": "script",
            "source_path": raw.source_path,
            "source_hash": raw.source_hash,
            "raw_content": raw.model_dump(mode="json"),
        },
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/{project_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    replace: bool = Form(default=False),
    language_hint: str | None = Form(default=None),
    service: InputService = Depends(get_input_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    data = await file.read()
    meta = service.ingest_pdf(
        project_id,
        filename=file.filename or "input.pdf",
        data=data,
        replace=replace,
        language_hint=language_hint,
    )
    return success_payload(
        meta.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/{project_id}/raw-content")
async def get_raw_content(
    project_id: str,
    request: Request,
    service: InputService = Depends(get_input_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    raw = service.get_raw_content(project_id)
    return success_payload(
        raw.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
