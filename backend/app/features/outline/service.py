"""TeachingOutlineService — RawContent → TeachingOutline (Phase 3.7)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.input.store import InputArtifactStore
from app.features.outline.budget import apply_word_budget, compute_total_word_budget
from app.features.outline.factory import create_outline_generator
from app.features.outline.protocols import OutlineGenerator
from app.features.outline.schemas import TeachingOutline
from app.features.outline.store import OutlineArtifactStore
from app.features.outline.validator import OutlineValidator
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.durations import resolve_target_duration_sec
from app.shared.pipeline_timing import timed_step

logger = get_logger(__name__)


class TeachingOutlineService:
    """Build a lesson-plan TeachingOutline from RawContent (no narration).

    Pipeline position: RawContent → TeachingOutline → EducationalScript.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: OutlineGenerator | None = None,
        validator: OutlineValidator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._outline_store = OutlineArtifactStore(self._fs)
        self._generator = generator or create_outline_generator(settings)
        self._validator = validator or OutlineValidator()

    def generate_outline(
        self,
        project_id: str,
        *,
        target_duration: str | None = None,
        target_duration_sec: int | None = None,
    ) -> TeachingOutline:
        """Create (or rebuild) a TeachingOutline for the project."""
        validate_project_id(project_id)
        self._require_project(project_id)
        raw = self._raw_store.read_raw_content(project_id)

        duration = resolve_target_duration_sec(
            label=target_duration,
            seconds=target_duration_sec,
        )
        total_words = compute_total_word_budget(duration)

        with timed_step("Outline"):
            outline = self._generator.generate(
                raw,
                target_duration_sec=duration,
                total_target_words=total_words,
            )
            outline = apply_word_budget(outline, total_target_words=total_words)
            outline = outline.model_copy(
                update={
                    "target_duration_sec": duration,
                    "total_target_words": total_words,
                }
            )
            self._validator.validate(outline, raw=raw)
            self._outline_store.write(project_id, outline)

        logger.info(
            "Teaching outline generated",
            extra={
                "event": "teaching_outline_generated",
                "project_id": project_id,
                "component": "teaching_outline",
                "outline_id": outline.outline_id,
                "section_count": len(outline.sections),
                "total_target_words": outline.total_target_words,
                "target_duration_sec": outline.target_duration_sec,
                "status": outline.status,
            },
        )
        return outline

    def get_outline(self, project_id: str) -> TeachingOutline:
        validate_project_id(project_id)
        self._require_project(project_id)
        return self._outline_store.read(project_id)

    def _require_project(self, project_id: str) -> None:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
