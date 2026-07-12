"""Persist EducationalScript + ScriptMetrics artifacts (Phase 3.6)."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import NotFoundError
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.script.metrics import ScriptMetricsCalculator
from app.features.script.schemas import EducationalScript, ScriptMetrics


class ScriptArtifactStore:
    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def script_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "educational_script.json"

    def markdown_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "educational_script.md"

    def metrics_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "script_metrics.json"

    def has_script(self, project_id: str) -> bool:
        return self.script_path(project_id).is_file()

    def write(
        self,
        project_id: str,
        script: EducationalScript,
        *,
        metrics: ScriptMetrics | None = None,
    ) -> Path:
        validate_project_id(project_id)
        root = self.artifacts_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)

        metrics = metrics or ScriptMetricsCalculator().compute(script)

        json_path = self.script_path(project_id)
        self._atomic_write_text(
            json_path,
            json.dumps(script.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        self._atomic_write_text(self.markdown_path(project_id), self._to_markdown(script))
        self._atomic_write_text(
            self.metrics_path(project_id),
            json.dumps(metrics.model_dump(mode="json"), indent=2, ensure_ascii=False),
        )
        return json_path

    def read(self, project_id: str) -> EducationalScript:
        validate_project_id(project_id)
        path = self.script_path(project_id)
        if not path.is_file():
            # Legacy Phase 3 path (one-time compatibility).
            legacy = self._fs.project_root(project_id) / "artifacts" / "v1" / "script.json"
            if legacy.is_file():
                raise NotFoundError(
                    "Legacy script.json found but Phase 3.6 requires educational_script.json. "
                    "Regenerate the script.",
                    code="SCRIPT_NOT_FOUND",
                    details={"project_id": project_id, "legacy_path": str(legacy)},
                )
            raise NotFoundError(
                "No educational script artifact for this project.",
                code="SCRIPT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return EducationalScript.model_validate_json(path.read_text(encoding="utf-8"))

    def read_metrics(self, project_id: str) -> ScriptMetrics:
        validate_project_id(project_id)
        path = self.metrics_path(project_id)
        if not path.is_file():
            raise NotFoundError(
                "No script metrics artifact for this project.",
                code="SCRIPT_METRICS_NOT_FOUND",
                details={"project_id": project_id},
            )
        return ScriptMetrics.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)

    @staticmethod
    def _to_markdown(script: EducationalScript) -> str:
        lines: list[str] = [
            f"# {script.title}",
            "",
            f"- Language: `{script.language}`",
            f"- Target duration: {script.target_duration_sec}s",
            f"- Estimated duration: {script.estimated_duration_sec}s",
            f"- Estimated words: {script.estimated_word_count}",
            f"- Estimated scenes: {script.estimated_scene_count}",
            "",
            "## Summary",
            "",
            script.summary.strip(),
            "",
        ]
        if script.learning_objectives:
            lines.extend(["## Learning objectives", ""])
            for item in script.learning_objectives:
                lines.append(f"- {item}")
            lines.append("")
        if script.key_concepts:
            lines.extend(["## Key concepts", ""])
            for concept in script.key_concepts:
                lines.append(f"- **{concept.label}** (`{concept.id}`)")
            lines.append("")
        lines.extend(["## Teaching sections", ""])
        for index, section in enumerate(script.teaching_sections, start=1):
            lines.extend(
                [
                    f"### {index}. {section.title}",
                    "",
                    f"_~{section.estimated_words} words · {section.estimated_duration_sec}s_",
                    "",
                    section.narration.strip(),
                    "",
                ]
            )
            if section.concept_tags:
                tags = ", ".join(section.concept_tags)
                lines.extend([f"Tags: {tags}", ""])
        return "\n".join(lines).rstrip() + "\n"
