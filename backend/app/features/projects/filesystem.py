"""Filesystem layout helpers for ExplainX projects."""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.enums import PROJECT_SUBDIRS
from app.core.errors import ExplainXError, NotFoundError, ValidationAppError
from app.core.logging import get_logger

logger = get_logger(__name__)

# UUID project ids only — prevents path segments like `..` or absolute paths.
_PROJECT_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Import archive limits (Zip Slip / Zip Bomb defenses).
MAX_IMPORT_ZIP_BYTES = 100 * 1024 * 1024
MAX_IMPORT_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_IMPORT_FILE_COUNT = 10_000
MAX_IMPORT_COMPRESSION_RATIO = 100.0


def validate_project_id(project_id: str) -> str:
    """Reject non-UUID ids that could escape the projects root."""
    if not project_id or not _PROJECT_ID_RE.fullmatch(project_id):
        raise ValidationAppError(
            "project_id must be a UUID.",
            code="VALIDATION_ERROR",
            details={"field": "project_id", "project_id": project_id},
        )
    return project_id


class ProjectFilesystem:
    """Owns on-disk project directories and project.json mirror."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _projects_base(self) -> Path:
        return self._settings.projects_dir.resolve()

    def _jail(self, candidate: Path, *, label: str) -> Path:
        """Ensure resolved path stays under the projects root."""
        base = self._projects_base()
        resolved = candidate.resolve()
        try:
            resolved.relative_to(base)
        except ValueError as exc:
            raise ValidationAppError(
                "Path escapes the projects storage root.",
                code="VALIDATION_ERROR",
                details={"field": label, "path": str(candidate)},
            ) from exc
        if resolved == base:
            raise ValidationAppError(
                "Path must target a project directory, not the projects root.",
                code="VALIDATION_ERROR",
                details={"field": label},
            )
        return resolved

    def project_root(self, project_id: str) -> Path:
        safe_id = validate_project_id(project_id)
        return self._jail(self._settings.projects_dir / safe_id, label="project_id")

    def relative_project_root(self, project_id: str) -> str:
        safe_id = validate_project_id(project_id)
        return f"projects/{safe_id}"

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
        path = self._jail(root / "project.json", label="project_json")
        tmp = self._jail(root / "temp" / "project.json.tmp", label="project_json_tmp")
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
        path = self._jail(self.project_root(project_id) / "project.json", label="project_json")
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
        # Destination must remain inside this project's tree (typically export/).
        dest_parent = self._jail(dest_zip.parent, label="export_path")
        dest_parent.mkdir(parents=True, exist_ok=True)
        safe_dest = self._jail(dest_parent / dest_zip.name, label="export_path")
        archive = shutil.make_archive(str(safe_dest.with_suffix("")), "zip", root_dir=root)
        return Path(archive)

    def extract_zip_safe(self, zip_path: Path, dest: Path) -> None:
        """Extract a zip into ``dest`` with Zip Slip and Zip Bomb protections."""
        dest_root = dest.resolve()
        dest_root.mkdir(parents=True, exist_ok=True)
        # Dest must be a project directory under the storage jail.
        self._jail(dest_root, label="import_dest")

        if not zip_path.is_file():
            raise NotFoundError("Import archive not found.", code="IMPORT_NOT_FOUND")

        compressed_size = zip_path.stat().st_size
        if compressed_size > MAX_IMPORT_ZIP_BYTES:
            raise ValidationAppError(
                "Import archive exceeds the maximum allowed size.",
                code="PROJECT_CORRUPTED",
                details={
                    "max_bytes": MAX_IMPORT_ZIP_BYTES,
                    "size_bytes": compressed_size,
                },
            )

        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                members = archive.infolist()
                if len(members) > MAX_IMPORT_FILE_COUNT:
                    raise ValidationAppError(
                        "Import archive contains too many files.",
                        code="PROJECT_CORRUPTED",
                        details={
                            "max_files": MAX_IMPORT_FILE_COUNT,
                            "file_count": len(members),
                        },
                    )

                uncompressed_total = 0
                for info in members:
                    uncompressed_total += max(info.file_size, 0)
                    if uncompressed_total > MAX_IMPORT_UNCOMPRESSED_BYTES:
                        raise ValidationAppError(
                            "Import archive uncompressed size exceeds the limit.",
                            code="PROJECT_CORRUPTED",
                            details={"max_uncompressed_bytes": MAX_IMPORT_UNCOMPRESSED_BYTES},
                        )
                    if info.compress_size > 0 and info.file_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > MAX_IMPORT_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
                            raise ValidationAppError(
                                "Import archive compression ratio looks unsafe.",
                                code="PROJECT_CORRUPTED",
                                details={"member": info.filename, "ratio": round(ratio, 2)},
                            )

                for info in members:
                    self._extract_zip_member(archive, info, dest_root)
        except zipfile.BadZipFile as exc:
            raise ValidationAppError(
                "Import archive is not a valid zip file.",
                code="PROJECT_CORRUPTED",
                details={"error": str(exc)},
            ) from exc

    def _extract_zip_member(
        self,
        archive: zipfile.ZipFile,
        info: zipfile.ZipInfo,
        dest_root: Path,
    ) -> None:
        name = info.filename.replace("\\", "/")
        if not name or name.endswith("/"):
            # Directory entry — create after jail check.
            if name:
                target_dir = self._resolve_zip_target(dest_root, name.rstrip("/"))
                target_dir.mkdir(parents=True, exist_ok=True)
            return

        if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
            raise ValidationAppError(
                "Import archive contains an absolute path (Zip Slip).",
                code="PROJECT_CORRUPTED",
                details={"member": info.filename},
            )
        if ".." in Path(name).parts:
            raise ValidationAppError(
                "Import archive contains a path traversal entry (Zip Slip).",
                code="PROJECT_CORRUPTED",
                details={"member": info.filename},
            )

        target = self._resolve_zip_target(dest_root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info, "r") as src, target.open("wb") as out:
            shutil.copyfileobj(src, out, length=1024 * 64)

    def _resolve_zip_target(self, dest_root: Path, relative_name: str) -> Path:
        candidate = (dest_root / relative_name).resolve()
        try:
            candidate.relative_to(dest_root)
        except ValueError as exc:
            raise ValidationAppError(
                "Import archive would extract outside the project directory (Zip Slip).",
                code="PROJECT_CORRUPTED",
                details={"member": relative_name},
            ) from exc
        return candidate
