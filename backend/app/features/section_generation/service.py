"""SectionGenerationService — TeachingOutline → EducationalScript (Phase 3.8)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.features.outline.schemas import TeachingOutline, TeachingSection
from app.features.outline.store import OutlineArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.quality.repair import ScriptRepairService
from app.features.quality.schemas import MAX_REPAIR_ATTEMPTS
from app.features.script.metrics import count_words
from app.features.script.schemas import EducationalScript
from app.features.section_generation.factory import create_section_generator
from app.features.section_generation.merger import SectionMerger
from app.features.section_generation.protocols import SectionGenerator
from app.features.section_generation.schemas import SectionOutput
from app.features.section_generation.store import SectionOutputStore
from app.features.section_generation.validator import SectionValidator

logger = get_logger(__name__)


class SectionGenerationService:
    """Generate EducationalScript by narrating each outline section independently.

    Pipeline: TeachingOutline → (per-section generate → validate → repair loop)
    → SectionMerger → EducationalScript.
    Never asks the LLM for the full script in one call.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: SectionGenerator | None = None,
        validator: SectionValidator | None = None,
        merger: SectionMerger | None = None,
        repair_service: ScriptRepairService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._outline_store = OutlineArtifactStore(self._fs)
        self._section_store = SectionOutputStore(self._fs)
        self._generator = generator or create_section_generator(settings)
        self._validator = validator or SectionValidator()
        self._merger = merger or SectionMerger()
        self._repair = repair_service or ScriptRepairService(settings)

    def generate_from_outline(
        self,
        project_id: str,
        *,
        outline: TeachingOutline | None = None,
    ) -> EducationalScript:
        """Generate section narrations, persist them, and merge into EducationalScript."""
        validate_project_id(project_id)
        self._require_project(project_id)
        plan = outline or self._outline_store.read(project_id)
        if plan.project_id != project_id:
            raise NotFoundError(
                "TeachingOutline project_id does not match requested project.",
                code="OUTLINE_NOT_FOUND",
                details={
                    "project_id": project_id,
                    "outline_project_id": plan.project_id,
                },
            )

        self._section_store.clear(project_id)
        outputs: list[SectionOutput] = []
        previous_summary = ""

        for index, section in enumerate(plan.sections, start=1):
            next_title = (
                plan.sections[index].title if index < len(plan.sections) else None
            )
            output = self._generate_with_repair_loop(
                outline=plan,
                section=section,
                index=index,
                previous_section_summary=previous_summary,
                next_section_title=next_title,
            )
            self._section_store.write(project_id, output)
            outputs.append(output)
            previous_summary = output.summary

            logger.info(
                "Section narration ready",
                extra={
                    "event": "section_narration_ready",
                    "project_id": project_id,
                    "index": index,
                    "outline_section_id": section.id,
                    "target_words": section.target_words,
                    "actual_words": count_words(output.narration),
                    "repair_attempt": output.metadata.get("repair_attempt", 0),
                },
            )

        script = self._merger.merge(plan, outputs)
        logger.info(
            "EducationalScript assembled from section outputs",
            extra={
                "event": "section_generation_merged",
                "project_id": project_id,
                "component": "section_generation",
                "script_id": script.script_id,
                "section_count": len(outputs),
                "estimated_word_count": script.estimated_word_count,
                "estimated_duration_sec": script.estimated_duration_sec,
            },
        )
        return script

    def list_section_outputs(self, project_id: str) -> list[SectionOutput]:
        validate_project_id(project_id)
        self._require_project(project_id)
        return self._section_store.list_outputs(project_id)

    def _generate_with_repair_loop(
        self,
        *,
        outline: TeachingOutline,
        section: TeachingSection,
        index: int,
        previous_section_summary: str,
        next_section_title: str | None,
    ) -> SectionOutput:
        """Generate → validate → repair (max 2) → revalidate for one section."""
        output = self._generator.generate_section(
            outline=outline,
            section=section,
            index=index,
            previous_section_summary=previous_section_summary,
            next_section_title=next_section_title,
        )
        errors = self._validator.collect_errors(
            output, expected=section, index=index
        )
        if not errors:
            return output

        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            logger.info(
                "Section validation failed; repairing",
                extra={
                    "event": "section_validation_repair",
                    "outline_section_id": section.id,
                    "index": index,
                    "attempt": attempt,
                    "errors": errors,
                    "actual_words": count_words(output.narration),
                    "target_words": section.target_words,
                },
            )
            output = self._repair.repair_section_output(
                output,
                expected=section,
                validation_errors=errors,
                previous_section_summary=previous_section_summary,
                next_section_title=next_section_title,
                attempt=attempt,
            )
            errors = self._validator.collect_errors(
                output, expected=section, index=index
            )
            if not errors:
                return output

        raise ValidationAppError(
            errors[0],
            code="SECTION_VALIDATION_ERROR",
            details={
                "section_id": section.id,
                "index": index,
                "actual_words": count_words(output.narration),
                "target_words": section.target_words,
                "errors": errors,
                "repair_attempts": MAX_REPAIR_ATTEMPTS,
            },
        )

    def _require_project(self, project_id: str) -> None:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
