"""Project HTTP routes — Phase 1.2."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from app.api.deps import get_project_service, settings_dep
from app.api.middleware.request_id import get_request_id
from app.core.config import Settings
from app.models.api.envelopes import success_payload
from app.models.api.projects import (
    ProjectCreateRequest,
    ProjectDuplicateRequest,
    ProjectRenameRequest,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    payload: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    detail = service.create(payload)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("")
async def list_projects(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    recent: bool = False,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    data = service.list_projects(status=status_filter, q=q, limit=limit, recent=recent)
    return success_payload(
        data.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/import")
async def import_project(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = None,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    suffix = Path(file.filename or "import.zip").suffix or ".zip"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        detail = service.import_project(tmp_path, title=title)
    finally:
        tmp_path.unlink(missing_ok=True)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    request: Request,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    detail = service.get(project_id)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    request: Request,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    detail = service.update(project_id, payload)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/{project_id}/rename")
async def rename_project(
    project_id: str,
    payload: ProjectRenameRequest,
    request: Request,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    detail = service.rename(project_id, payload)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/{project_id}/save")
async def save_project(
    project_id: str,
    request: Request,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    detail = service.save(project_id)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    mode: str = Query(default="soft", pattern="^(soft|hard)$"),
    confirm: bool = False,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    result = service.delete(project_id, mode=mode, confirm=confirm)
    return success_payload(
        result,
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/{project_id}/archive")
async def archive_project(
    project_id: str,
    request: Request,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    detail = service.archive(project_id)
    return success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.post("/{project_id}/duplicate")
async def duplicate_project(
    project_id: str,
    request: Request,
    payload: ProjectDuplicateRequest = ProjectDuplicateRequest(),
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> JSONResponse:
    detail = service.duplicate(project_id, payload)
    body = success_payload(
        detail.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=body)


@router.post("/{project_id}/export")
async def export_project(
    project_id: str,
    request: Request,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> dict[str, Any]:
    manifest = service.export_project(project_id)
    return success_payload(
        manifest.model_dump(mode="json"),
        request_id=get_request_id(request),
        api_version=settings.api_version,
    )


@router.get("/{project_id}/export/zip")
async def download_export_zip(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
    settings: Settings = Depends(settings_dep),
) -> FileResponse:
    manifest = service.export_project(project_id)
    path = settings.data_root_path / manifest.export_path
    return FileResponse(
        path,
        media_type="application/zip",
        filename=path.name,
    )
