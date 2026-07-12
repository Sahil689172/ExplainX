"""SectionGenerationService — TeachingOutline → EducationalScript (Phase 3.8)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.outline.schemas import TeachingOutline
from app.features.outline.store import OutlineArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.metrics import count_words
from app.features.script.schemas import EducationalScript
from app.features.section_generation.factory import create_section_generator
from app.features.section_generation.merger import SectionMerger
from app.features.section_generation.protocols import SectionAssurer, SectionGenerator
from app.features.section_generation.store import SectionOutputStore
from app.shared.pipeline_timing import timed_step
from app.shared.section_output import SectionOutput
from app.shared.section_validator import SectionValidator

logger = get_logger(__name__)


class SectionGenerationService:
    """Generate EducationalScript by narrating each outline section independently.

    Responsible ONLY for generation (+ optional injected assurance).
    Never imports quality modules — inject a ``SectionAssurer`` for
    validate → repair → revalidate.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: SectionGenerator | None = None,
        validator: SectionValidator | None = None,
        merger: SectionMerger | None = None,
        section_assurer: SectionAssurer | None = None,
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
        self._assurer = section_assurer

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
            with timed_step(f"Section {index}"):
                output = self._generator.generate_section(
                    outline=plan,
                    section=section,
                    index=index,
                    previous_section_summary=previous_summary,
                    next_section_title=next_title,
                )
                if self._assurer is not None:
                    output = self._assurer.assure_section(
                        output,
                        expected=section,
                        index=index,
                        previous_section_summary=previous_summary,
                        next_section_title=next_title,
                    )
                else:
                    with timed_step("Validator"):
                        self._validator.validate(output, expected=section, index=index)

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

    def _require_project(self, project_id: str) -> None:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
