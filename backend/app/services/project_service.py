"""Project lifecycle service — create/open/rename/delete/duplicate/save/load/archive/export/import."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import DSL_VERSION, PROJECT_SCHEMA_VERSION, ProjectPhase, ProjectStatus, SourceType
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.timeutil import utc_now_iso
from app.db.models import Project, ProjectSettings
from app.models.api.projects import (
    ExportManifest,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectDuplicateRequest,
    ProjectListData,
    ProjectRenameRequest,
    ProjectSettingsIn,
    ProjectSummary,
    ProjectUpdateRequest,
)
from app.repositories.project_repository import ProjectRepository
from app.services.project_filesystem import ProjectFilesystem
from app.services.project_serializer import ProjectSerializer
from app.services.project_validator import ProjectValidator

logger = get_logger(__name__)


class ProjectService:
    """Application service for project management only (no AI / render)."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._serializer = ProjectSerializer(self._fs)
        self._validator = ProjectValidator(session)

    def create(self, payload: ProjectCreateRequest) -> ProjectDetail:
        self._validator.validate_create(payload)
        project_id = str(uuid.uuid4())
        now = utc_now_iso()
        source_hash = ""
        if payload.source_topic:
            digest = hashlib.sha256(payload.source_topic.strip().encode("utf-8")).hexdigest()[:16]
            source_hash = f"topic:{digest}"

        project = Project(
            project_id=project_id,
            title=payload.title,
            description=payload.description,
            status=ProjectStatus.DRAFT.value,
            current_phase=ProjectPhase.FOUNDATION.value,
            source_type=payload.source_type.value,
            source_topic=payload.source_topic,
            source_hash=source_hash,
            theme_id=payload.theme_id,
            source_language_code=payload.source_language_code,
            target_language_code=payload.target_language_code,
            voice_id=payload.voice_id,
            difficulty=payload.difficulty.value if payload.difficulty else None,
            project_root=self._fs.relative_project_root(project_id),
            project_version="1.0.0",
            dsl_version=DSL_VERSION,
            schema_version=PROJECT_SCHEMA_VERSION,
            created_at=now,
            updated_at=now,
        )
        project.settings = self._build_settings(project_id, payload.settings, now)
        self._repo.add(project)
        self._fs.ensure_project_tree(project_id)
        self._session.flush()
        self._write_mirror(project)
        self._session.commit()
        self._session.refresh(project)
        logger.info(
            "Project Created",
            extra={
                "event": "project_created",
                "project_id": project_id,
                "component": "project_service",
            },
        )
        return self._serializer.to_detail(project)

    def list_projects(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        limit: int = 20,
        recent: bool = False,
    ) -> ProjectListData:
        limit = max(1, min(limit, 100))
        items = self._repo.list(status=status, q=q, limit=limit, recent_only=recent)
        summaries = [self._serializer.to_summary(p) for p in items]
        return ProjectListData(
            items=summaries,
            page={"limit": limit, "next_cursor": None, "total_estimate": self._repo.count_active()},
        )

    def get(self, project_id: str) -> ProjectDetail:
        project = self._require(project_id)
        missing = self._fs.validate_tree(project_id)
        if missing:
            repaired = self._fs.repair_tree(project_id)
            logger.warning(
                "Recovered missing project folders on open",
                extra={
                    "event": "project_recovered_folders",
                    "project_id": project_id,
                    "component": "project_service",
                },
            )
            if repaired:
                self.save(project_id)
        logger.info(
            "Project Loaded",
            extra={"event": "project_loaded", "project_id": project_id, "component": "project_service"},
        )
        return self._serializer.to_detail(project)

    def update(self, project_id: str, payload: ProjectUpdateRequest) -> ProjectDetail:
        project = self._require(project_id)
        if project.status == ProjectStatus.ARCHIVED.value and payload.title:
            raise ConflictError(
                "Archived projects cannot be edited. Restore status first.",
                code="INVALID_STATE_TRANSITION",
                details={"status": project.status},
            )
        self._validator.validate_update(payload, project_id=project_id)
        if payload.title is not None:
            project.title = payload.title
        if payload.description is not None:
            project.description = payload.description
        if payload.theme_id is not None:
            project.theme_id = payload.theme_id
        if payload.voice_id is not None:
            project.voice_id = payload.voice_id
        if payload.difficulty is not None:
            project.difficulty = payload.difficulty.value
        if payload.target_language_code is not None:
            project.target_language_code = payload.target_language_code
        if payload.source_topic is not None:
            project.source_topic = payload.source_topic
        if payload.settings is not None:
            now = utc_now_iso()
            if project.settings is None:
                project.settings = self._build_settings(project_id, payload.settings, now)
            else:
                self._apply_settings(project.settings, payload.settings, now)
        project.updated_at = utc_now_iso()
        self._write_mirror(project)
        self._session.commit()
        self._session.refresh(project)
        logger.info(
            "Project Saved",
            extra={"event": "project_saved", "project_id": project_id, "component": "project_service"},
        )
        return self._serializer.to_detail(project)

    def rename(self, project_id: str, payload: ProjectRenameRequest) -> ProjectDetail:
        detail = self.update(project_id, ProjectUpdateRequest(title=payload.title))
        logger.info(
            "Project Renamed",
            extra={"event": "project_renamed", "project_id": project_id, "component": "project_service"},
        )
        return detail

    def save(self, project_id: str) -> ProjectDetail:
        project = self._require(project_id)
        project.updated_at = utc_now_iso()
        self._fs.ensure_project_tree(project_id)
        self._write_mirror(project)
        self._session.commit()
        self._session.refresh(project)
        logger.info(
            "Project Saved",
            extra={"event": "project_saved", "project_id": project_id, "component": "project_service"},
        )
        return self._serializer.to_detail(project)

    def delete(self, project_id: str, *, mode: str = "soft", confirm: bool = False) -> dict[str, Any]:
        project = self._require(project_id)
        if mode == "hard":
            if not confirm:
                raise ValidationAppError(
                    "Hard delete requires confirm=true.",
                    code="VALIDATION_ERROR",
                    details={"field": "confirm"},
                )
            self._session.delete(project)
            self._session.commit()
            self._fs.delete_tree(project_id, hard=True)
            logger.info(
                "Project Deleted",
                extra={
                    "event": "project_deleted",
                    "project_id": project_id,
                    "component": "project_service",
                },
            )
            return {"project_id": project_id, "deleted": True, "mode": "hard"}

        project.deleted_at = utc_now_iso()
        project.updated_at = project.deleted_at
        self._write_mirror(project)
        self._session.commit()
        logger.info(
            "Project Deleted",
            extra={"event": "project_deleted", "project_id": project_id, "component": "project_service"},
        )
        return {"project_id": project_id, "deleted": True, "mode": "soft"}

    def archive(self, project_id: str) -> ProjectDetail:
        project = self._require(project_id)
        project.status = ProjectStatus.ARCHIVED.value
        project.updated_at = utc_now_iso()
        self._write_mirror(project)
        self._session.commit()
        self._session.refresh(project)
        logger.info(
            "Project Archived",
            extra={"event": "project_archived", "project_id": project_id, "component": "project_service"},
        )
        return self._serializer.to_detail(project)

    def duplicate(
        self, project_id: str, payload: ProjectDuplicateRequest | None = None
    ) -> ProjectDetail:
        source = self._require(project_id)
        new_title = (payload.title if payload and payload.title else f"{source.title} (Copy)").strip()
        self._validator.ensure_unique_title(new_title)
        new_id = str(uuid.uuid4())
        now = utc_now_iso()
        self._fs.copy_tree(project_id, new_id)

        clone = Project(
            project_id=new_id,
            title=new_title,
            description=source.description,
            status=ProjectStatus.DRAFT.value,
            current_phase=ProjectPhase.FOUNDATION.value,
            source_type=source.source_type,
            source_path=source.source_path,
            source_topic=source.source_topic,
            source_hash=source.source_hash,
            theme_id=source.theme_id,
            source_language_code=source.source_language_code,
            target_language_code=source.target_language_code,
            voice_id=source.voice_id,
            difficulty=source.difficulty,
            project_root=self._fs.relative_project_root(new_id),
            project_version=source.project_version,
            dsl_version=source.dsl_version,
            schema_version=source.schema_version,
            created_at=now,
            updated_at=now,
        )
        if source.settings:
            clone.settings = ProjectSettings(
                project_id=new_id,
                export_width=source.settings.export_width,
                export_height=source.settings.export_height,
                fps=source.settings.fps,
                quality_profile=source.settings.quality_profile,
                burn_in_subtitles=source.settings.burn_in_subtitles,
                subtitle_formats=source.settings.subtitle_formats,
                speaking_rate=source.settings.speaking_rate,
                max_scenes=source.settings.max_scenes,
                plugin_flags=source.settings.plugin_flags,
                extra_json=source.settings.extra_json,
                updated_at=now,
            )
        self._repo.add(clone)
        self._session.flush()
        self._write_mirror(clone)
        self._session.commit()
        self._session.refresh(clone)
        logger.info(
            "Project Duplicated",
            extra={
                "event": "project_duplicated",
                "project_id": new_id,
                "component": "project_service",
            },
        )
        return self._serializer.to_detail(clone)

    def export_project(self, project_id: str) -> ExportManifest:
        project = self._require(project_id)
        self.save(project_id)
        export_dir = self._fs.project_root(project_id) / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / f"{project_id}-package.zip"
        archive = self._fs.export_zip(project_id, zip_path)
        logger.info(
            "Project Exported",
            extra={"event": "project_exported", "project_id": project_id, "component": "project_service"},
        )
        return ExportManifest(
            project_id=project_id,
            export_path=str(Path("projects") / project_id / "export" / archive.name),
            files=[
                {"role": "package", "path": str(Path("projects") / project_id / "export" / archive.name)},
                {"role": "metadata", "path": str(Path("projects") / project_id / "project.json")},
            ],
        )

    def import_project(self, zip_path: Path, *, title: str | None = None) -> ProjectDetail:
        if not zip_path.exists():
            raise NotFoundError("Import archive not found.", code="IMPORT_NOT_FOUND")
        new_id = str(uuid.uuid4())
        dest = self._fs.project_root(new_id)
        dest.mkdir(parents=True, exist_ok=True)
        try:
            shutil.unpack_archive(str(zip_path), extract_dir=dest)
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(dest, ignore_errors=True)
            raise ValidationAppError(
                "Failed to unpack project archive.",
                code="PROJECT_CORRUPTED",
                details={"error": str(exc)},
            ) from exc

        mirror_path = dest / "project.json"
        if not mirror_path.exists():
            # search one level deep
            candidates = list(dest.rglob("project.json"))
            if not candidates:
                shutil.rmtree(dest, ignore_errors=True)
                raise ValidationAppError(
                    "Imported archive missing project.json.",
                    code="PROJECT_CORRUPTED",
                )
            # normalize: move contents of parent of project.json to dest root if nested
            mirror_path = candidates[0]

        try:
            payload = json.loads(mirror_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            shutil.rmtree(dest, ignore_errors=True)
            raise ValidationAppError(
                "Corrupted project.json in import.",
                code="PROJECT_CORRUPTED",
                details={"error": str(exc)},
            ) from exc

        project_data = payload.get("project") or payload
        imported_title = title or str(project_data.get("title") or "Imported Project")
        self._validator.ensure_unique_title(imported_title)
        theme_id = str(project_data.get("theme_id") or "notebooklm")
        source_lang = str(project_data.get("source_language_code") or "en")
        target_lang = str(project_data.get("target_language_code") or "en")
        self._validator.ensure_theme(theme_id)
        self._validator.ensure_language(source_lang)
        self._validator.ensure_language(target_lang)

        now = utc_now_iso()
        settings_data = project_data.get("settings") or {}
        create_settings = ProjectSettingsIn(
            export_width=int(settings_data.get("export_width", 1280)),
            export_height=int(settings_data.get("export_height", 720)),
            fps=float(settings_data.get("fps", 30)),
            quality_profile=settings_data.get("quality_profile", "standard"),
            burn_in_subtitles=bool(settings_data.get("burn_in_subtitles", False)),
            subtitle_formats=list(settings_data.get("subtitle_formats") or ["srt", "vtt"]),
            speaking_rate=float(settings_data.get("speaking_rate", 1.0)),
            max_scenes=settings_data.get("max_scenes"),
        )

        project = Project(
            project_id=new_id,
            title=imported_title,
            description=project_data.get("description"),
            status=ProjectStatus.DRAFT.value,
            current_phase=ProjectPhase.FOUNDATION.value,
            source_type=str(project_data.get("source_type") or SourceType.TOPIC.value),
            source_topic=project_data.get("source_topic"),
            source_hash=str(project_data.get("source_hash") or "import"),
            theme_id=theme_id,
            source_language_code=source_lang,
            target_language_code=target_lang,
            voice_id=project_data.get("voice_id"),
            difficulty=project_data.get("difficulty"),
            project_root=self._fs.relative_project_root(new_id),
            project_version=str(payload.get("project_version") or "1.0.0"),
            dsl_version=str(payload.get("dsl_version") or DSL_VERSION),
            schema_version=str(payload.get("schema_version") or PROJECT_SCHEMA_VERSION),
            created_at=now,
            updated_at=now,
        )
        project.settings = self._build_settings(new_id, create_settings, now)
        self._repo.add(project)
        self._fs.ensure_project_tree(new_id)
        self._session.flush()
        self._write_mirror(project)
        self._session.commit()
        self._session.refresh(project)
        logger.info(
            "Project Imported",
            extra={"event": "project_imported", "project_id": new_id, "component": "project_service"},
        )
        return self._serializer.to_detail(project)

    def load_mirror(self, project_id: str) -> dict[str, Any]:
        """Load project.json; attempt recovery if DB row exists but mirror broken."""
        project = self._require(project_id)
        try:
            return self._fs.read_project_json(project_id)
        except ValidationAppError:
            # regenerate mirror from DB
            self._write_mirror(project)
            self._session.commit()
            logger.warning(
                "Regenerated corrupted project.json from database",
                extra={
                    "event": "project_mirror_recovered",
                    "project_id": project_id,
                    "component": "project_service",
                },
            )
            return self._fs.read_project_json(project_id)

    def _require(self, project_id: str) -> Project:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return project

    def _write_mirror(self, project: Project) -> None:
        self._fs.write_project_json(project.project_id, self._serializer.to_mirror_dict(project))

    def _build_settings(
        self, project_id: str, settings: ProjectSettingsIn, now: str
    ) -> ProjectSettings:
        return ProjectSettings(
            project_id=project_id,
            export_width=settings.export_width,
            export_height=settings.export_height,
            fps=settings.fps,
            quality_profile=settings.quality_profile.value
            if hasattr(settings.quality_profile, "value")
            else str(settings.quality_profile),
            burn_in_subtitles=1 if settings.burn_in_subtitles else 0,
            subtitle_formats=json.dumps(settings.subtitle_formats),
            speaking_rate=settings.speaking_rate,
            max_scenes=settings.max_scenes,
            updated_at=now,
        )

    def _apply_settings(self, row: ProjectSettings, settings: ProjectSettingsIn, now: str) -> None:
        row.export_width = settings.export_width
        row.export_height = settings.export_height
        row.fps = settings.fps
        row.quality_profile = (
            settings.quality_profile.value
            if hasattr(settings.quality_profile, "value")
            else str(settings.quality_profile)
        )
        row.burn_in_subtitles = 1 if settings.burn_in_subtitles else 0
        row.subtitle_formats = json.dumps(settings.subtitle_formats)
        row.speaking_rate = settings.speaking_rate
        row.max_scenes = settings.max_scenes
        row.updated_at = now
