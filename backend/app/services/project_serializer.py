"""Serialize ORM projects to API / filesystem payloads."""

from __future__ import annotations

import json
from typing import Any

from app.core.enums import ProjectPhase, ProjectStatus, SourceType
from app.db.models import Project, ProjectSettings
from app.models.api.projects import ProjectDetail, ProjectSettingsOut, ProjectSummary
from app.services.project_filesystem import ProjectFilesystem


def _parse_formats(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(v) for v in value]
    except json.JSONDecodeError:
        pass
    return ["srt", "vtt"]


class ProjectSerializer:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def settings_out(self, settings: ProjectSettings | None) -> ProjectSettingsOut:
        if settings is None:
            return ProjectSettingsOut(
                export_width=1280,
                export_height=720,
                fps=30.0,
                quality_profile="standard",
                burn_in_subtitles=False,
                subtitle_formats=["srt", "vtt"],
                speaking_rate=1.0,
                max_scenes=None,
            )
        return ProjectSettingsOut(
            export_width=settings.export_width,
            export_height=settings.export_height,
            fps=settings.fps,
            quality_profile=settings.quality_profile,
            burn_in_subtitles=bool(settings.burn_in_subtitles),
            subtitle_formats=_parse_formats(settings.subtitle_formats),
            speaking_rate=settings.speaking_rate,
            max_scenes=settings.max_scenes,
        )

    def to_summary(self, project: Project) -> ProjectSummary:
        return ProjectSummary(
            project_id=project.project_id,
            title=project.title,
            description=project.description,
            status=ProjectStatus(project.status),
            current_phase=ProjectPhase(project.current_phase),
            theme_id=project.theme_id,
            source_language_code=project.source_language_code,
            target_language_code=project.target_language_code,
            updated_at=project.updated_at,
            created_at=project.created_at,
            actual_duration_sec=project.actual_duration_sec,
            thumbnail_url=None,
        )

    def to_detail(self, project: Project) -> ProjectDetail:
        root = self._fs.relative_project_root(project.project_id)
        dirs = self._fs.directory_map(project.project_id)
        summary = self.to_summary(project)
        return ProjectDetail(
            **summary.model_dump(),
            source_type=SourceType(project.source_type),
            source_topic=project.source_topic,
            source_path=project.source_path,
            voice_id=project.voice_id,
            difficulty=project.difficulty,
            project_root=root,
            assets_directory=dirs["assets"],
            output_directory=dirs["export"],
            project_version=project.project_version,
            dsl_version=project.dsl_version,
            schema_version=project.schema_version,
            settings=self.settings_out(project.settings),
            directories=dirs,
            configuration={
                "theme_id": project.theme_id,
                "voice_id": project.voice_id,
                "difficulty": project.difficulty,
                "source_language_code": project.source_language_code,
                "target_language_code": project.target_language_code,
                "settings": self.settings_out(project.settings).model_dump(),
            },
        )

    def to_mirror_dict(self, project: Project) -> dict[str, Any]:
        detail = self.to_detail(project)
        return {
            "schema_version": project.schema_version,
            "dsl_version": project.dsl_version,
            "project_version": project.project_version,
            "project": detail.model_dump(mode="json"),
        }
