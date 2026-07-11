"""Persist source files and RawContent artifacts under a project tree."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError, ValidationAppError
from app.features.input.schemas import RawContent
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id

RAW_CONTENT_RELATIVE = "artifacts/v1/raw_content.json"
TOPIC_SOURCE_FILENAME = "topic.txt"
SCRIPT_SOURCE_FILENAME = "script.txt"


class InputArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def source_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "source"

    def raw_content_path(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts" / "v1" / "raw_content.json"

    def has_raw_content(self, project_id: str) -> bool:
        return self.raw_content_path(project_id).is_file()

    def write_text_source(self, project_id: str, filename: str, text: str) -> str:
        validate_project_id(project_id)
        root = self._fs.ensure_project_tree(project_id)
        source = root / "source"
        source.mkdir(parents=True, exist_ok=True)
        path = source / filename
        # Jail: must stay under source/
        resolved = path.resolve()
        try:
            resolved.relative_to((root / "source").resolve())
        except ValueError as exc:
            raise ValidationAppError(
                "Source filename escapes project source directory.",
                code="VALIDATION_ERROR",
                details={"filename": filename},
            ) from exc
        path.write_text(text, encoding="utf-8")
        return f"projects/{project_id}/source/{filename}"

    def write_bytes_source(self, project_id: str, filename: str, data: bytes) -> str:
        validate_project_id(project_id)
        safe_name = Path(filename).name
        if not safe_name or safe_name in {".", ".."}:
            raise ValidationAppError(
                "Invalid upload filename.",
                code="VALIDATION_ERROR",
                details={"filename": filename},
            )
        root = self._fs.ensure_project_tree(project_id)
        source = root / "source"
        source.mkdir(parents=True, exist_ok=True)
        path = (source / safe_name).resolve()
        try:
            path.relative_to(source.resolve())
        except ValueError as exc:
            raise ValidationAppError(
                "Source filename escapes project source directory.",
                code="VALIDATION_ERROR",
                details={"filename": safe_name},
            ) from exc
        path.write_bytes(data)
        return f"projects/{project_id}/source/{safe_name}"

    def absolute_source_path(self, project_id: str, relative_project_path: str) -> Path:
        """Resolve ``projects/{id}/source/...`` to an absolute jailed path."""
        validate_project_id(project_id)
        prefix = f"projects/{project_id}/"
        if not relative_project_path.startswith(prefix):
            raise ValidationAppError(
                "source_path does not belong to this project.",
                code="VALIDATION_ERROR",
                details={"source_path": relative_project_path},
            )
        rel = relative_project_path[len(prefix) :]
        candidate = (self._fs.project_root(project_id) / rel).resolve()
        base = self._fs.project_root(project_id).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise ValidationAppError(
                "Resolved source path escapes project root.",
                code="VALIDATION_ERROR",
            ) from exc
        return candidate

    def write_raw_content(self, project_id: str, content: RawContent) -> Path:
        validate_project_id(project_id)
        path = self.raw_content_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(content.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
        return path

    def read_raw_content(self, project_id: str) -> RawContent:
        path = self.raw_content_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No raw content artifact for this project.",
                code="RAW_CONTENT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return RawContent.model_validate_json(path.read_text(encoding="utf-8"))
