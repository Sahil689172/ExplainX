"""Persist EducationalScript artifacts under a project tree."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.script.schemas import EducationalScript


class ScriptArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def script_path(self, project_id: str) -> Path:
        # Aligns with constitution artifacts/.../script.json naming.
        return self._fs.project_root(project_id) / "artifacts" / "v1" / "script.json"

    def has_script(self, project_id: str) -> bool:
        return self.script_path(project_id).is_file()

    def write(self, project_id: str, script: EducationalScript) -> Path:
        validate_project_id(project_id)
        path = self.script_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(script.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
        return path

    def read(self, project_id: str) -> EducationalScript:
        validate_project_id(project_id)
        path = self.script_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No educational script artifact for this project.",
                code="SCRIPT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return EducationalScript.model_validate_json(path.read_text(encoding="utf-8"))
