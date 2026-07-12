"""Persist per-section narration artifacts (Phase 3.8)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.shared.section_output import SectionOutput


class SectionOutputStore:
    """Write ``artifacts/section_outputs/section_XX.json`` files."""

    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def section_outputs_dir(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "section_outputs"

    def section_path(self, project_id: str, index: int) -> Path:
        return self.section_outputs_dir(project_id) / f"section_{index:02d}.json"

    def clear(self, project_id: str) -> None:
        validate_project_id(project_id)
        root = self.section_outputs_dir(project_id)
        if root.is_dir():
            shutil.rmtree(root)

    def write(self, project_id: str, output: SectionOutput) -> Path:
        validate_project_id(project_id)
        root = self.section_outputs_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.section_path(project_id, output.index)
        self._atomic_write_text(
            path,
            json.dumps(output.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        return path

    def read(self, project_id: str, index: int) -> SectionOutput:
        validate_project_id(project_id)
        path = self.section_path(project_id, index)
        if not path.is_file():
            raise NotFoundError(
                "No section output artifact for this index.",
                code="SECTION_OUTPUT_NOT_FOUND",
                details={"project_id": project_id, "index": index},
            )
        return SectionOutput.model_validate_json(path.read_text(encoding="utf-8"))

    def list_outputs(self, project_id: str) -> list[SectionOutput]:
        validate_project_id(project_id)
        root = self.section_outputs_dir(project_id)
        if not root.is_dir():
            return []
        outputs: list[SectionOutput] = []
        for path in sorted(root.glob("section_*.json")):
            outputs.append(SectionOutput.model_validate_json(path.read_text(encoding="utf-8")))
        return sorted(outputs, key=lambda item: item.index)

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
