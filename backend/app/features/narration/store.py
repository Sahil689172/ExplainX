"""Persist continuous narration artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.narration.languages import CANONICAL_SCRIPT_LANGUAGE
from app.features.narration.schemas import NarrationDocument
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id


class NarrationArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def json_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "narration.json"

    def text_path(self, project_id: str, lang: str = CANONICAL_SCRIPT_LANGUAGE) -> Path:
        """Return ``narration_<lang>.txt``.

        Backwards compatible: for English, also recognize legacy ``narration.txt``.
        """
        code = (lang or CANONICAL_SCRIPT_LANGUAGE).strip().lower()[:2] or "en"
        return self.artifacts_dir(project_id) / f"narration_{code}.txt"

    def legacy_text_path(self, project_id: str) -> Path:
        """Pre-multilingual English artifact path."""
        return self.artifacts_dir(project_id) / "narration.txt"

    def resolve_english_text_path(self, project_id: str) -> Path | None:
        """Prefer ``narration_en.txt``; fall back to legacy ``narration.txt``."""
        modern = self.text_path(project_id, "en")
        if modern.is_file() and modern.stat().st_size > 0:
            return modern
        legacy = self.legacy_text_path(project_id)
        if legacy.is_file() and legacy.stat().st_size > 0:
            return legacy
        return None

    def write_text(self, project_id: str, lang: str, text: str) -> Path:
        """Write plain ``narration_<lang>.txt`` (atomic)."""
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        path = self.text_path(project_id, lang)
        tmp = path.with_suffix(path.suffix + ".tmp")
        body = text if text.endswith("\n") else text + "\n"
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(path)
        if (lang or "en").strip().lower()[:2] == "en":
            # Keep legacy filename for older readers during transition.
            legacy = self.legacy_text_path(project_id)
            legacy_tmp = legacy.with_suffix(legacy.suffix + ".tmp")
            legacy_tmp.write_text(body, encoding="utf-8")
            legacy_tmp.replace(legacy)
        return path

    def read_text(self, project_id: str, lang: str = CANONICAL_SCRIPT_LANGUAGE) -> str | None:
        """Read ``narration_<lang>.txt``; English also checks legacy ``narration.txt``."""
        validate_project_id(project_id)
        code = (lang or "en").strip().lower()[:2] or "en"
        if code == "en":
            path = self.resolve_english_text_path(project_id)
        else:
            path = self.text_path(project_id, code)
            if path is None or not path.is_file():
                return None
        if path is None:
            return None
        return path.read_text(encoding="utf-8")

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
        # Canonical English plain-text artifact.
        self.write_text(project_id, CANONICAL_SCRIPT_LANGUAGE, narration.text)
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
