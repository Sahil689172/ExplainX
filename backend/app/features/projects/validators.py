"""Project input and reference-data validation."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import SourceType
from app.core.errors import ConflictError, ValidationAppError
from app.db.models import Language, Project, ProjectSettings, Theme
from app.features.projects.schemas import (
    ProjectCreateRequest,
    ProjectSettingsIn,
    ProjectSettingsPatch,
    ProjectUpdateRequest,
)


class ProjectValidator:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_theme(self, theme_id: str) -> None:
        theme = self._session.get(Theme, theme_id)
        if theme is None or not theme.is_enabled:
            raise ValidationAppError(
                f"Unknown or disabled theme: {theme_id}",
                code="UNKNOWN_THEME",
                details={"theme_id": theme_id},
            )

    def ensure_language(self, code: str) -> None:
        language = self._session.get(Language, code)
        if language is None or not language.is_enabled:
            raise ValidationAppError(
                f"Unknown or disabled language: {code}",
                code="UNKNOWN_LANGUAGE",
                details={"language_code": code},
            )

    def ensure_unique_title(self, title: str, *, exclude_project_id: str | None = None) -> None:
        stmt = select(Project).where(
            func.lower(Project.title) == title.lower(),
            Project.deleted_at.is_(None),
        )
        if exclude_project_id:
            stmt = stmt.where(Project.project_id != exclude_project_id)
        existing = self._session.scalars(stmt).first()
        if existing is not None:
            raise ConflictError(
                f"A project named '{title}' already exists.",
                code="DUPLICATE_PROJECT",
                details={"title": title, "existing_project_id": existing.project_id},
            )

    def validate_create(self, payload: ProjectCreateRequest) -> None:
        self.ensure_unique_title(payload.title)
        self.ensure_theme(payload.theme_id)
        self.ensure_language(payload.source_language_code)
        self.ensure_language(payload.target_language_code)
        if payload.source_type == SourceType.TOPIC and not (payload.source_topic or "").strip():
            raise ValidationAppError(
                "source_topic is required when source_type is topic.",
                code="SOURCE_REQUIRED",
                details={"field": "source_topic"},
            )
        self.validate_settings(payload.settings)

    def validate_update(self, payload: ProjectUpdateRequest, *, project_id: str) -> None:
        if payload.title is not None:
            self.ensure_unique_title(payload.title, exclude_project_id=project_id)
        if payload.theme_id is not None:
            self.ensure_theme(payload.theme_id)
        if payload.target_language_code is not None:
            self.ensure_language(payload.target_language_code)
        if payload.settings is not None:
            self.validate_settings_patch(payload.settings)

    def validate_settings(self, settings: ProjectSettingsIn) -> None:
        self._ensure_even_dimensions(settings.export_width, settings.export_height)

    def validate_settings_patch(self, settings: ProjectSettingsPatch) -> None:
        if settings.export_width is not None and settings.export_width % 2 != 0:
            raise ValidationAppError(
                "export dimensions must be even numbers for video encoders.",
                code="VALIDATION_ERROR",
                details={"export_width": settings.export_width},
            )
        if settings.export_height is not None and settings.export_height % 2 != 0:
            raise ValidationAppError(
                "export dimensions must be even numbers for video encoders.",
                code="VALIDATION_ERROR",
                details={"export_height": settings.export_height},
            )

    def validate_merged_dimensions(self, row: ProjectSettings) -> None:
        self._ensure_even_dimensions(row.export_width, row.export_height)

    @staticmethod
    def _ensure_even_dimensions(width: int, height: int) -> None:
        if width % 2 != 0 or height % 2 != 0:
            raise ValidationAppError(
                "export dimensions must be even numbers for video encoders.",
                code="VALIDATION_ERROR",
                details={"export_width": width, "export_height": height},
            )
