"""Persist continuous narration artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.narration.schemas import NarrationDocument
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id


class NarrationArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def json_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "narration.json"

    def text_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "narration.txt"

    def write(self, project_id: str, narration: NarrationDocument) -> Path:
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.json_path(project_id)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(narration.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
        text_path = self.text_path(project_id)
        text_tmp = text_path.with_suffix(text_path.suffix + ".tmp")
        text_tmp.write_text(narration.text, encoding="utf-8")
        text_tmp.replace(text_path)
        return path

    def read(self, project_id: str) -> NarrationDocument:
        validate_project_id(project_id)
        path = self.json_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No narration artifact for this project.",
                code="NARRATION_NOT_FOUND",
                details={"project_id": project_id},
            )
        return NarrationDocument.model_validate_json(path.read_text(encoding="utf-8"))
