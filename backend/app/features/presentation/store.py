"""Persist PresentationPlan artifacts under a project tree."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.presentation.schemas import PresentationPlan
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id


class PresentationPlanStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def plan_path(self, project_id: str) -> Path:
        return (
            self._fs.project_root(project_id) / "artifacts" / "v1" / "presentation_plan.json"
        )

    def has_plan(self, project_id: str) -> bool:
        return self.plan_path(project_id).is_file()

    def write(self, project_id: str, plan: PresentationPlan) -> Path:
        validate_project_id(project_id)
        path = self.plan_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
        return path

    def read(self, project_id: str) -> PresentationPlan:
        validate_project_id(project_id)
        path = self.plan_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No presentation plan artifact for this project.",
                code="PRESENTATION_PLAN_NOT_FOUND",
                details={"project_id": project_id},
            )
        return PresentationPlan.model_validate_json(path.read_text(encoding="utf-8"))
