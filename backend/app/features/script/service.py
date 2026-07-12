"""ContentIntelligenceService — any supported input → EducationalScript (Phase 3)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import ProjectPhase, SourceType
from app.core.errors import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.timeutil import utc_now_iso
from app.features.input.pdf_extract import (
    SCRIPT_MAX_LEN,
    SCRIPT_MIN_LEN,
    TOPIC_MAX_LEN,
    TOPIC_MIN_LEN,
    inspect_pdf,
    validate_pdf_size,
)
from app.features.input.schemas import RawContent
from app.features.input.store import InputArtifactStore
from app.features.presentation.schemas import PresentationPlan
from app.features.presentation.store import PresentationPlanStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.durations import V1_TARGET_DURATION_SEC, resolve_target_duration_sec
from app.features.script.factory import create_content_generator
from app.features.script.metrics import ScriptMetricsCalculator, enrich_script_with_metrics
from app.features.script.processors.pdf_processor import PDFContentProcessor
from app.features.script.processors.script_processor import ScriptContentProcessor
from app.features.script.processors.topic_processor import TopicContentProcessor
from app.features.script.protocols import ContentGenerator, ContentProcessor
from app.features.script.schemas import EducationalScript
from app.features.script.store import ScriptArtifactStore
from app.features.script.validator import ScriptValidator

logger = get_logger(__name__)


class ContentIntelligenceService:
    """Generate one EducationalScript from topic / PDF / custom script.

    Phase 3.6 standardizes on a single V1 format: a 2–3 minute explainer
    (120–180s, ~320–420 words). Optional duration request fields are ignored.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: ContentGenerator | None = None,
        validator: ScriptValidator | None = None,
        processors: dict[SourceType, ContentProcessor] | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._plan_store = PresentationPlanStore(self._fs)
        self._script_store = ScriptArtifactStore(self._fs)
        self._metrics = ScriptMetricsCalculator()
        self._generator = generator or create_content_generator(settings)
        self._validator = validator or ScriptValidator()
        self._processors: dict[SourceType, ContentProcessor] = processors or {
            SourceType.TOPIC: TopicContentProcessor(self._generator),
            SourceType.SCRIPT: ScriptContentProcessor(self._generator),
            SourceType.PDF: PDFContentProcessor(self._generator),
        }

    def generate_script(
        self,
        project_id: str,
        *,
        target_duration: str | None = None,
        target_duration_sec: int | None = None,
    ) -> EducationalScript:
        validate_project_id(project_id)
        project = self._require_project(project_id)
        raw = self._raw_store.read_raw_content(project_id)
        self._validate_raw_input(raw)

        # V1: always the canonical 2–3 minute target (request fields ignored).
        duration = resolve_target_duration_sec(
            label=target_duration,
            seconds=target_duration_sec,
        )
        plan = self._optional_plan(project_id)
        pdf_path = self._resolve_pdf_path(project_id, raw)

        processor = self._processors.get(raw.source_type)
        if processor is None:
            raise ValidationAppError(
                f"No content processor for source_type={raw.source_type.value}.",
                code="UNSUPPORTED_SOURCE_TYPE",
                details={"source_type": raw.source_type.value},
            )

        script = processor.process(
            raw,
            target_duration_sec=duration,
            plan=plan,
            pdf_path=pdf_path,
        )
        script = enrich_script_with_metrics(
            script.model_copy(update={"target_duration_sec": V1_TARGET_DURATION_SEC})
        )
        metrics = self._metrics.compute(script)
        self._validator.validate(script, raw=raw)
        self._script_store.write(project_id, script, metrics=metrics)

        try:
            project.current_phase = ProjectPhase.CONTENT.value
            project.updated_at = utc_now_iso()
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        logger.info(
            "Educational script generated",
            extra={
                "event": "educational_script_generated",
                "project_id": project_id,
                "component": "content_intelligence",
                "script_id": script.script_id,
                "source_type": script.source_type.value,
                "status": script.status,
                "target_duration_sec": V1_TARGET_DURATION_SEC,
                "estimated_duration_sec": script.estimated_duration_sec,
                "estimated_word_count": script.estimated_word_count,
            },
        )
        return script

    def get_script(self, project_id: str) -> EducationalScript:
        validate_project_id(project_id)
        self._require_project(project_id)
        return self._script_store.read(project_id)

    def _validate_raw_input(self, raw: RawContent) -> None:
        text = raw.text.strip()
        if raw.source_type == SourceType.TOPIC:
            length = len(text)
            if length < TOPIC_MIN_LEN or length > TOPIC_MAX_LEN:
                raise ValidationAppError(
                    f"Topic length must be between {TOPIC_MIN_LEN} and {TOPIC_MAX_LEN} characters.",
                    code="VALIDATION_ERROR",
                    details={
                        "field": "topic",
                        "length": length,
                        "min": TOPIC_MIN_LEN,
                        "max": TOPIC_MAX_LEN,
                    },
                )
        elif raw.source_type == SourceType.SCRIPT:
            length = len(text)
            if length < SCRIPT_MIN_LEN or length > SCRIPT_MAX_LEN:
                raise ValidationAppError(
                    f"Script length must be between {SCRIPT_MIN_LEN} and {SCRIPT_MAX_LEN} characters.",
                    code="VALIDATION_ERROR",
                    details={
                        "field": "script",
                        "length": length,
                        "min": SCRIPT_MIN_LEN,
                        "max": SCRIPT_MAX_LEN,
                    },
                )
        elif raw.source_type == SourceType.PDF:
            # File-level checks when the source PDF is still on disk.
            path = self._resolve_pdf_path(raw.project_id, raw)
            if path is not None and path.is_file():
                validate_pdf_size(path.stat().st_size)
                inspect_pdf(path)
            elif not text:
                raise ValidationAppError(
                    "PDF produced no extractable text.",
                    code="PARSER_EMPTY_CONTENT",
                    details={"project_id": raw.project_id},
                )

    def _resolve_pdf_path(self, project_id: str, raw: RawContent) -> Path | None:
        if raw.source_type != SourceType.PDF or not raw.source_path:
            return None
        try:
            return self._raw_store.absolute_source_path(project_id, raw.source_path)
        except ValidationAppError:
            return None

    def _optional_plan(self, project_id: str) -> PresentationPlan | None:
        try:
            return self._plan_store.read(project_id)
        except NotFoundError:
            return None

    def _require_project(self, project_id: str):
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return project


# Backward-compatible alias for older imports / deps.
ScriptGenerationService = ContentIntelligenceService
