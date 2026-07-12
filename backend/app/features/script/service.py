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
from app.features.outline.service import TeachingOutlineService
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.quality.service import QualityAssuranceService
from app.features.script.durations import V1_TARGET_DURATION_SEC, resolve_target_duration_sec
from app.features.script.metrics import ScriptMetricsCalculator, enrich_script_with_metrics
from app.features.script.schemas import EducationalScript
from app.features.script.store import ScriptArtifactStore
from app.features.section_generation.service import SectionGenerationService

logger = get_logger(__name__)


class ContentIntelligenceService:
    """Generate, assemble, and quality-assure EducationalScript.

    Phase 3.9 pipeline:
    RawContent → TeachingOutline → SectionGeneration → EducationalScript
      → ScriptMetricsCalculator → QualityAssuranceService → Approved EducationalScript.

    Public HTTP APIs are unchanged.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        outline_service: TeachingOutlineService | None = None,
        section_service: SectionGenerationService | None = None,
        quality_service: QualityAssuranceService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._script_store = ScriptArtifactStore(self._fs)
        self._metrics = ScriptMetricsCalculator()
        self._outline_service = outline_service or TeachingOutlineService(session, settings)
        self._section_service = section_service or SectionGenerationService(session, settings)
        self._quality_service = quality_service or QualityAssuranceService(session, settings)

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

        _ = resolve_target_duration_sec(
            label=target_duration,
            seconds=target_duration_sec,
        )

        outline = self._outline_service.generate_outline(
            project_id,
            target_duration=target_duration,
            target_duration_sec=target_duration_sec,
        )

        script = self._section_service.generate_from_outline(
            project_id,
            outline=outline,
        )
        script = enrich_script_with_metrics(
            script.model_copy(
                update={
                    "target_duration_sec": V1_TARGET_DURATION_SEC,
                    "metadata": {
                        **(script.metadata or {}),
                        "teaching_outline_id": outline.outline_id,
                        "outline_section_count": len(outline.sections),
                        "outline_total_target_words": outline.total_target_words,
                        "section_generation": True,
                    },
                }
            )
        )

        # Phase 3.9: metrics + validate + optional targeted repair → approved script.
        approved = self._quality_service.assure(
            project_id,
            script,
            raw=raw,
            outline=outline,
        )
        metrics = self._metrics.compute(approved)
        self._script_store.write(project_id, approved, metrics=metrics)

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
                "script_id": approved.script_id,
                "source_type": approved.source_type.value,
                "status": approved.status,
                "target_duration_sec": V1_TARGET_DURATION_SEC,
                "estimated_duration_sec": approved.estimated_duration_sec,
                "estimated_word_count": approved.estimated_word_count,
                "section_generation": True,
                "quality_assured": True,
            },
        )
        return approved

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

    def _require_project(self, project_id: str):
        project = self._repo.get(project_id)
        if project is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
        return project


ScriptGenerationService = ContentIntelligenceService
