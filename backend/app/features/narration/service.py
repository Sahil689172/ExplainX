"""NarrationGenerationService — RawContent → continuous NarrationDocument."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.input.schemas import RawContent
from app.features.input.store import InputArtifactStore
from app.features.narration.factory import create_narration_generator
from app.features.narration.protocols import NarrationGenerator
from app.features.narration.schemas import NarrationDocument
from app.features.narration.store import NarrationArtifactStore
from app.features.narration.validator import NarrationValidator
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.durations import resolve_target_duration_sec
from app.shared.pipeline_timing import timed_step

logger = get_logger(__name__)


class NarrationGenerationService:
    """Produce continuous narration (one LLM call for topic/PDF; none for script)."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: NarrationGenerator | None = None,
        validator: NarrationValidator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._store = NarrationArtifactStore(self._fs)
        self._generator = generator or create_narration_generator(settings)
        self._validator = validator or NarrationValidator()

    def generate(
        self,
        project_id: str,
        *,
        raw: RawContent | None = None,
        target_duration_sec: int | None = None,
        repair_hint: str | None = None,
    ) -> NarrationDocument:
        validate_project_id(project_id)
        self._require_project(project_id)
        content = raw or self._raw_store.read_raw_content(project_id)
        duration = target_duration_sec or resolve_target_duration_sec()

        with timed_step("Narration"):
            narration = self._generator.generate(
                content,
                target_duration_sec=duration,
                repair_hint=repair_hint,
            )
            self._validator.validate(narration)
            self._store.write(project_id, narration)

        logger.info(
            "Narration ready",
            extra={
                "event": "narration_generated",
                "project_id": project_id,
                "narration_id": narration.narration_id,
                "source_type": narration.source_type.value,
                "llm": bool((narration.metadata or {}).get("llm")),
            },
        )
        return narration

    def _require_project(self, project_id: str) -> None:
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
