"""Persist QA artifacts (Phase 3.9)."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.quality.schemas import QualityReport, RepairLog
from app.features.script.schemas import EducationalScript


class QualityArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def quality_report_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "quality_report.json"

    def approved_script_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "approved_script.json"

    def repair_log_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "repair_log.json"

    def write_report(self, project_id: str, report: QualityReport) -> Path:
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.quality_report_path(project_id)
        self._atomic_write_text(
            path,
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        return path

    def write_approved(self, project_id: str, script: EducationalScript) -> Path:
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.approved_script_path(project_id)
        self._atomic_write_text(
            path,
            json.dumps(script.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        return path

    def write_repair_log(self, project_id: str, log: RepairLog) -> Path:
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.repair_log_path(project_id)
        self._atomic_write_text(
            path,
            json.dumps(log.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        return path

    def read_report(self, project_id: str) -> QualityReport:
        validate_project_id(project_id)
        path = self.quality_report_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No quality report artifact for this project.",
                code="QUALITY_REPORT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return QualityReport.model_validate_json(path.read_text(encoding="utf-8"))

    def read_approved(self, project_id: str) -> EducationalScript:
        validate_project_id(project_id)
        path = self.approved_script_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No approved script artifact for this project.",
                code="APPROVED_SCRIPT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return EducationalScript.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
