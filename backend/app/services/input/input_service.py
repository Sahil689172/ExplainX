"""InputService — validate, route, persist, associate RawContent with a project."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import ProjectPhase, SourceType
from app.core.errors import ConflictError, ExplainXError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.timeutil import utc_now_iso
from app.models.api.inputs import DocumentUploadMeta, ScriptSourceRequest, TopicSourceRequest
from app.models.artifacts.raw_content import RawContent
from app.repositories.project_repository import ProjectRepository
from app.services.input.input_artifact_store import (
    SCRIPT_SOURCE_FILENAME,
    TOPIC_SOURCE_FILENAME,
    InputArtifactStore,
)
from app.services.input.input_router import InputRouter
from app.services.input.processors.base import ProcessorContext, sha256_bytes, sha256_text
from app.services.project_filesystem import ProjectFilesystem, validate_project_id

logger = get_logger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
PDF_EXTENSIONS = {".pdf"}


class InputService:
    """Phase 2.1 / 2.2 Input Intelligence application service (no AI)."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        router: InputRouter | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._store = InputArtifactStore(self._fs)
        self._router = router or InputRouter()

    def ingest_topic(self, project_id: str, payload: TopicSourceRequest) -> RawContent:
        validate_project_id(project_id)
        project = self._require_project(project_id)
        self._ensure_can_replace(project_id, replace=payload.replace)

        relative = self._store.write_text_source(
            project_id, TOPIC_SOURCE_FILENAME, payload.topic
        )
        ctx = ProcessorContext(
            project_id=project_id,
            source_type=SourceType.TOPIC,
            topic=payload.topic,
            language_hint=payload.language_hint,
            source_path_relative=relative,
            source_hash=sha256_text(payload.topic),
        )
        raw = self._router.route(ctx)
        return self._persist_association(
            project_id=project_id,
            raw=raw,
            source_type=SourceType.TOPIC,
            source_path=relative,
            source_topic=payload.topic,
            source_hash=raw.source_hash,
        )

    def ingest_script(self, project_id: str, payload: ScriptSourceRequest) -> RawContent:
        validate_project_id(project_id)
        self._require_project(project_id)
        self._ensure_can_replace(project_id, replace=payload.replace)

        relative = self._store.write_text_source(
            project_id, SCRIPT_SOURCE_FILENAME, payload.script
        )
        ctx = ProcessorContext(
            project_id=project_id,
            source_type=SourceType.SCRIPT,
            script_text=payload.script,
            language_hint=payload.language_hint,
            source_path_relative=relative,
            source_hash=sha256_text(payload.script),
            extra={"title": payload.title},
        )
        raw = self._router.route(ctx)
        return self._persist_association(
            project_id=project_id,
            raw=raw,
            source_type=SourceType.SCRIPT,
            source_path=relative,
            source_topic=payload.title,
            source_hash=raw.source_hash,
        )

    def ingest_pdf(
        self,
        project_id: str,
        *,
        filename: str,
        data: bytes,
        replace: bool = False,
        language_hint: str | None = None,
    ) -> DocumentUploadMeta:
        validate_project_id(project_id)
        self._require_project(project_id)
        self._ensure_can_replace(project_id, replace=replace)

        if len(data) == 0:
            raise ValidationAppError(
                "Uploaded file is empty.",
                code="VALIDATION_ERROR",
                details={"field": "file"},
            )
        if len(data) > MAX_UPLOAD_BYTES:
            raise ExplainXError(
                "Upload exceeds the maximum allowed size.",
                code="UPLOAD_TOO_LARGE",
                status_code=413,
                details={"max_bytes": MAX_UPLOAD_BYTES, "size_bytes": len(data)},
            )

        suffix = Path(filename).suffix.lower()
        if suffix not in PDF_EXTENSIONS:
            raise ExplainXError(
                "Only PDF uploads are supported in Phase 2.1/2.2.",
                code="UNSUPPORTED_SOURCE_TYPE",
                status_code=415,
                details={"filename": filename, "extension": suffix},
            )

        safe_name = Path(filename).name or "input.pdf"
        if not safe_name.lower().endswith(".pdf"):
            safe_name = f"{safe_name}.pdf"

        relative = self._store.write_bytes_source(project_id, safe_name, data)
        absolute = self._store.absolute_source_path(project_id, relative)
        ctx = ProcessorContext(
            project_id=project_id,
            source_type=SourceType.PDF,
            file_path=absolute,
            original_filename=filename,
            language_hint=language_hint,
            source_path_relative=relative,
            source_hash=sha256_bytes(data),
        )
        raw = self._router.route(ctx)
        raw = self._persist_association(
            project_id=project_id,
            raw=raw,
            source_type=SourceType.PDF,
            source_path=relative,
            source_topic=None,
            source_hash=raw.source_hash,
        )
        return DocumentUploadMeta(
            project_id=project_id,
            source_type=SourceType.PDF.value,
            source_path=relative,
            source_hash=raw.source_hash,
            size_bytes=len(data),
            filename=safe_name,
            raw_content=raw,
        )

    def get_raw_content(self, project_id: str) -> RawContent:
        validate_project_id(project_id)
        self._require_project(project_id)
        return self._store.read_raw_content(project_id)

    def _persist_association(
        self,
        *,
        project_id: str,
        raw: RawContent,
        source_type: SourceType,
        source_path: str,
        source_topic: str | None,
        source_hash: str,
    ) -> RawContent:
        project = self._require_project(project_id)
        meta = dict(raw.metadata)
        meta["raw_document_id"] = raw.content_id
        raw = raw.model_copy(update={"metadata": meta, "source_path": source_path})

        try:
            self._store.write_raw_content(project_id, raw)
            project.source_type = source_type.value
            project.source_path = source_path
            project.source_topic = source_topic
            project.source_hash = source_hash
            project.current_phase = ProjectPhase.DOCUMENT.value
            project.updated_at = utc_now_iso()
            self._session.commit()
            self._session.refresh(project)
        except Exception:
            self._session.rollback()
            raise

        logger.info(
            "Input ingested",
            extra={
                "event": "input_ingested",
                "project_id": project_id,
                "component": "input_service",
                "source_type": source_type.value,
                "content_id": raw.content_id,
            },
        )
        return raw

    def _require_project(self, project_id: str):
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return project

    def _ensure_can_replace(self, project_id: str, *, replace: bool) -> None:
        if replace:
            return
        if self._store.has_raw_content(project_id):
            raise ConflictError(
                "Project already has source content. Pass replace=true to overwrite.",
                code="SOURCE_ALREADY_EXISTS",
                details={"project_id": project_id},
            )
