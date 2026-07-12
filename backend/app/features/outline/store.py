"""Persist TeachingOutline artifact (Phase 3.7)."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.outline.schemas import TeachingOutline
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id


class OutlineArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def outline_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "teaching_outline.json"

    def has_outline(self, project_id: str) -> bool:
        return self.outline_path(project_id).is_file()

    def write(self, project_id: str, outline: TeachingOutline) -> Path:
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.outline_path(project_id)
        self._atomic_write_text(
            path,
            json.dumps(outline.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        return path

    def read(self, project_id: str) -> TeachingOutline:
        validate_project_id(project_id)
        path = self.outline_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No teaching outline artifact for this project.",
                code="OUTLINE_NOT_FOUND",
                details={"project_id": project_id},
            )
        return TeachingOutline.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
