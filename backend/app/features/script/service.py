"""ScriptGenerationService — RawContent → EducationalScript."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.input.store import InputArtifactStore
from app.features.presentation.schemas import PresentationPlan
from app.features.presentation.store import PresentationPlanStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.generator import PlaceholderScriptGenerator
from app.features.script.protocols import ScriptGenerator
from app.features.script.schemas import EducationalScript
from app.features.script.store import ScriptArtifactStore
from app.features.script.validator import ScriptValidator

logger = get_logger(__name__)


class ScriptGenerationService:
    """Normalize project input and produce a common EducationalScript.

    Input types (topic / PDF / custom script) are already unified as
    ``RawContent`` by Input Intelligence. This service:

    1. Loads RawContent (required)
    2. Optionally loads PresentationPlan (concepts / title)
    3. Delegates to ``ScriptGenerator`` (placeholder today; Ollama later)
    4. Validates and persists ``artifacts/v1/script.json``
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: ScriptGenerator | None = None,
        validator: ScriptValidator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._plan_store = PresentationPlanStore(self._fs)
        self._script_store = ScriptArtifactStore(self._fs)
        self._generator = generator or PlaceholderScriptGenerator()
        self._validator = validator or ScriptValidator()

    def generate_script(self, project_id: str) -> EducationalScript:
        validate_project_id(project_id)
        self._require_project(project_id)
        raw = self._raw_store.read_raw_content(project_id)
        plan = self._optional_plan(project_id)

        script = self._generator.generate(raw, plan=plan)
        self._validator.validate(script, raw=raw)
        self._script_store.write(project_id, script)

        logger.info(
            "Educational script generated",
            extra={
                "event": "educational_script_generated",
                "project_id": project_id,
                "component": "script_generation",
                "script_id": script.script_id,
                "source_type": script.source_type.value,
                "status": script.status,
            },
        )
        return script

    def get_script(self, project_id: str) -> EducationalScript:
        validate_project_id(project_id)
        self._require_project(project_id)
        return self._script_store.read(project_id)

    def _optional_plan(self, project_id: str) -> PresentationPlan | None:
        try:
            return self._plan_store.read(project_id)
        except NotFoundError:
            return None

    def _require_project(self, project_id: str) -> None:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
