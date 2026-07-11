"""ContentIntelligenceService — RawContent → PresentationPlan (Phase 2.3)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.input.store import InputArtifactStore
from app.features.presentation.planner import PlaceholderPresentationPlanner
from app.features.presentation.protocols import PresentationPlanner
from app.features.presentation.schemas import PresentationPlan
from app.features.presentation.store import PresentationPlanStore
from app.features.presentation.validators import PresentationPlanValidator
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository

logger = get_logger(__name__)


class ContentIntelligenceService:
    """Orchestrates analyzers behind ``PresentationPlanner``.

    Phase 2.3 uses a deterministic placeholder planner. Swap in an LLM-backed
    ``PresentationPlanner`` later without changing this service's public API.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        planner: PresentationPlanner | None = None,
        validator: PresentationPlanValidator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._plan_store = PresentationPlanStore(self._fs)
        self._planner = planner or PlaceholderPresentationPlanner()
        self._validator = validator or PresentationPlanValidator()

    def generate_plan(self, project_id: str) -> PresentationPlan:
        """Build (or rebuild) a PresentationPlan from the project's RawContent."""
        validate_project_id(project_id)
        self._require_project(project_id)
        raw = self._raw_store.read_raw_content(project_id)

        plan = self._planner.plan(raw)
        self._validator.validate(plan, raw=raw)
        self._plan_store.write(project_id, plan)

        logger.info(
            "Presentation plan generated",
            extra={
                "event": "presentation_plan_generated",
                "project_id": project_id,
                "component": "content_intelligence",
                "plan_id": plan.plan_id,
                "status": plan.status,
            },
        )
        return plan

    def get_plan(self, project_id: str) -> PresentationPlan:
        validate_project_id(project_id)
        self._require_project(project_id)
        return self._plan_store.read(project_id)

    def _require_project(self, project_id: str) -> None:
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
