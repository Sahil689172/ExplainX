"""SingleScriptGenerationService — TeachingOutline → EducationalScript (one pass)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.outline.schemas import TeachingOutline
from app.features.outline.store import OutlineArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.schemas import EducationalScript
from app.features.single_script.factory import create_single_script_generator
from app.features.single_script.protocols import SingleScriptGenerator
from app.shared.pipeline_timing import timed_step

logger = get_logger(__name__)


class SingleScriptGenerationService:
    """Generate EducationalScript from TeachingOutline in a single generator call.

    Does not run quality assurance — that remains QualityAssuranceService.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: SingleScriptGenerator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._outline_store = OutlineArtifactStore(self._fs)
        self._generator = generator or create_single_script_generator(settings)

    def generate_from_outline(
        self,
        project_id: str,
        *,
        outline: TeachingOutline | None = None,
    ) -> EducationalScript:
        """Generate full script narration from outline (one LLM call when Ollama)."""
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

        with timed_step("SingleScript"):
            script = self._generator.generate(plan)

        logger.info(
            "EducationalScript assembled via single-pass generation",
            extra={
                "event": "single_script_generation_complete",
                "project_id": project_id,
                "component": "single_script_generation",
                "script_id": script.script_id,
                "section_count": len(script.teaching_sections),
                "estimated_word_count": script.estimated_word_count,
                "estimated_duration_sec": script.estimated_duration_sec,
                "single_script_generation": True,
            },
        )
        return script

    def _require_project(self, project_id: str) -> None:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
