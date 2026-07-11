"""Filesystem layout helpers for ExplainX projects."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.enums import PROJECT_SUBDIRS
from app.core.errors import ExplainXError, NotFoundError, ValidationAppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProjectFilesystem:
    """Owns on-disk project directories and project.json mirror."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def project_root(self, project_id: str) -> Path:
        return self._settings.projects_dir / project_id

    def relative_project_root(self, project_id: str) -> str:
        return f"projects/{project_id}"

    def ensure_project_tree(self, project_id: str) -> Path:
        root = self.project_root(project_id)
        try:
            root.mkdir(parents=True, exist_ok=True)
            for name in PROJECT_SUBDIRS:
                (root / name).mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise ExplainXError(
                "Permission denied while creating project folders.",
                code="PROJECT_PERMISSION_DENIED",
                status_code=500,
                details={"project_id": project_id, "path": str(root)},
            ) from exc
        except OSError as exc:
            raise ExplainXError(
                "Failed to create project folders.",
                code="PROJECT_FOLDER_ERROR",
                status_code=500,
                details={"project_id": project_id, "error": str(exc)},
            ) from exc
        return root

    def validate_tree(self, project_id: str) -> list[str]:
        """Return list of missing required subdirectories."""
        root = self.project_root(project_id)
        if not root.exists():
            return ["__root__"]
        missing = [name for name in PROJECT_SUBDIRS if not (root / name).is_dir()]
        return missing

    def repair_tree(self, project_id: str) -> list[str]:
        """Recreate missing folders; return what was repaired."""
        missing = self.validate_tree(project_id)
        if not missing:
            return []
        self.ensure_project_tree(project_id)
        logger.warning(
            "project_folders_repaired",
            extra={
                "event": "project_folders_repaired",
                "project_id": project_id,
                "component": "project_filesystem",
            },
        )
        return missing

    def write_project_json(self, project_id: str, payload: dict[str, Any]) -> Path:
        root = self.ensure_project_tree(project_id)
        path = root / "project.json"
        tmp = root / "temp" / "project.json.tmp"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            raise ExplainXError(
                "Failed to write project.json.",
                code="PROJECT_SAVE_FAILED",
                status_code=500,
                details={"project_id": project_id, "error": str(exc)},
            ) from exc
        return path

    def read_project_json(self, project_id: str) -> dict[str, Any]:
        path = self.project_root(project_id) / "project.json"
        if not path.exists():
            raise NotFoundError(
                "project.json missing for project.",
                code="PROJECT_MIRROR_MISSING",
                details={"project_id": project_id},
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationAppError(
                "Corrupted project.json metadata.",
                code="PROJECT_CORRUPTED",
                details={"project_id": project_id, "error": str(exc)},
            ) from exc

    def delete_tree(self, project_id: str, *, hard: bool = False) -> None:
        root = self.project_root(project_id)
        if not root.exists():
            return
        if hard:
            shutil.rmtree(root, ignore_errors=False)

    def copy_tree(self, source_id: str, dest_id: str) -> Path:
        src = self.project_root(source_id)
        dest = self.project_root(dest_id)
        if not src.exists():
            raise NotFoundError(
                "Source project folder missing.",
                code="PROJECT_FOLDER_MISSING",
                details={"project_id": source_id},
            )
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return dest

    def directory_map(self, project_id: str) -> dict[str, str]:
        root = self.relative_project_root(project_id)
        return {name: f"{root}/{name}" for name in PROJECT_SUBDIRS}

    def export_zip(self, project_id: str, dest_zip: Path) -> Path:
        root = self.project_root(project_id)
        if not root.exists():
            raise NotFoundError(
                "Project folder missing.",
                code="PROJECT_FOLDER_MISSING",
                details={"project_id": project_id},
            )
        dest_zip.parent.mkdir(parents=True, exist_ok=True)
        archive = shutil.make_archive(str(dest_zip.with_suffix("")), "zip", root_dir=root)
        return Path(archive)
