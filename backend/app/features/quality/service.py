"""QualityAssuranceService — metrics, validate, repair loop, approve (Phase 3.9)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.core.logging import get_logger
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.outline.schemas import TeachingOutline
from app.features.outline.schemas import TeachingSection as OutlineTeachingSection
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.quality.inspector import QualityInspector, readability_score_from_level
from app.features.quality.repair import ScriptRepairService
from app.features.quality.schemas import (
    MAX_REPAIR_ATTEMPTS,
    FinalStatus,
    QualityFinding,
    QualityReport,
    RepairAction,
    RepairLog,
    RepairLogEntry,
    ValidationStatus,
)
from app.features.quality.store import QualityArtifactStore
from app.features.script.metrics import (
    ScriptMetricsCalculator,
    count_words,
    enrich_script_with_metrics,
)
from app.features.script.schemas import EducationalScript
from app.features.script.validator import ScriptValidator
from app.shared.pipeline_timing import timed_step
from app.shared.section_output import SectionOutput
from app.shared.section_validator import SectionValidator

logger = get_logger(__name__)

_HARD_CODES = {
    "TOO_SHORT",
    "TOO_LONG",
    "EMPTY_SECTION",
    "DUPLICATE_SECTION_IDS",
    "MISSING_SECTIONS",
    "MISSING_OUTLINE_SECTIONS",
}

# Only these findings drive repair in MVP.
_REPAIRABLE_CODES = {
    "TOO_SHORT",
    "EMPTY_SECTION",
}

# Optional full-script rebuild (e.g. regenerate narration + SceneBuilder).
# Returns (script, optional refreshed outline).
ScriptRebuilder = Callable[
    [EducationalScript, list[QualityFinding], int],
    tuple[EducationalScript, TeachingOutline | None],
]


class QualityAssuranceService:
    """Gate EducationalScript quality before downstream consumers.

    Orchestrates per-section validation/repair (``assure_section``) and
    script-level QA (``assure``).

    Pipeline position:
    EducationalScript → ScriptMetricsCalculator → QA → Approved EducationalScript
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        inspector: QualityInspector | None = None,
        repair_service: ScriptRepairService | None = None,
        script_validator: ScriptValidator | None = None,
        section_validator: SectionValidator | None = None,
        calculator: ScriptMetricsCalculator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._fs = ProjectFilesystem(settings)
        self._store = QualityArtifactStore(self._fs)
        self._inspector = inspector or QualityInspector(
            min_duration_sec=settings.script_min_duration_sec,
            max_duration_sec=settings.script_max_duration_sec,
        )
        self._repair = repair_service or ScriptRepairService(settings)
        self._validator = script_validator or ScriptValidator(
            min_duration_sec=settings.script_min_duration_sec,
            max_duration_sec=settings.script_max_duration_sec,
        )
        self._section_validator = section_validator or SectionValidator()
        self._calculator = calculator or ScriptMetricsCalculator()

    def assure_section(
        self,
        output: SectionOutput,
        *,
        expected: OutlineTeachingSection,
        index: int,
        previous_section_summary: str,
        next_section_title: str | None,
    ) -> SectionOutput:
        """Validate one section; repair up to 2 times; revalidate.

        Implements ``SectionAssurer`` so SectionGenerationService can inject
        this without importing quality modules.
        """
        with timed_step("Validator"):
            errors = self._section_validator.collect_errors(
                output, expected=expected, index=index
            )
        if not errors:
            return output

        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            logger.info(
                "Section validation failed; repairing",
                extra={
                    "event": "section_validation_repair",
                    "outline_section_id": expected.id,
                    "index": index,
                    "attempt": attempt,
                    "errors": errors,
                    "actual_words": count_words(output.narration),
                    "target_words": expected.target_words,
                },
            )
            with timed_step(f"Repair {attempt}"):
                output = self._repair.repair_section_output(
                    output,
                    expected=expected,
                    validation_errors=errors,
                    previous_section_summary=previous_section_summary,
                    next_section_title=next_section_title,
                    attempt=attempt,
                )
            with timed_step("Validator"):
                errors = self._section_validator.collect_errors(
                    output, expected=expected, index=index
                )
            if not errors:
                return output

        raise ValidationAppError(
            errors[0],
            code="SECTION_VALIDATION_ERROR",
            details={
                "section_id": expected.id,
                "index": index,
                "actual_words": count_words(output.narration),
                "target_words": expected.target_words,
                "errors": errors,
                "repair_attempts": MAX_REPAIR_ATTEMPTS,
            },
        )

    def assure(
        self,
        project_id: str,
        script: EducationalScript,
        *,
        raw: RawContent | None = None,
        outline: TeachingOutline | None = None,
        script_rebuilder: ScriptRebuilder | None = None,
    ) -> EducationalScript:
        """Run QA; repair up to 2 times; return approved script or raise.

        When ``script_rebuilder`` is provided (narration pipeline), repair
        regenerates the whole EducationalScript from new narration + SceneBuilder
        instead of per-section LLM edits.
        """
        validate_project_id(project_id)
        current = enrich_script_with_metrics(script)
        current_outline = outline
        repair_entries = []
        attempts = 0

        while True:
            findings, errors, warnings, empty, missing = self._inspector.inspect(
                current, outline=current_outline
            )
            actionable = [
                f
                for f in findings
                if f.repair_action is not None
                and f.code in _REPAIRABLE_CODES
                and (script_rebuilder is not None or f.section_id)
            ]
            unrecoverable = any(f.code == "MISSING_OUTLINE_SECTIONS" for f in findings)
            has_hard_issue = any(f.code in _HARD_CODES for f in findings)

            if not has_hard_issue and not unrecoverable:
                try:
                    with timed_step("Validator"):
                        self._validator.validate(current, raw=raw)
                except ValidationAppError as exc:
                    errors = list(errors) + [exc.message]
                    findings, errors2, warnings2, empty, missing = self._inspector.inspect(
                        current, outline=current_outline
                    )
                    errors = list(dict.fromkeys(errors + errors2 + [exc.message]))
                    warnings = list(dict.fromkeys(warnings + warnings2))
                    actionable = [
                        f
                        for f in findings
                        if f.repair_action is not None
                        and f.code in _REPAIRABLE_CODES
                        and (script_rebuilder is not None or f.section_id)
                    ]
                    has_hard_issue = True
                else:
                    approved = enrich_script_with_metrics(
                        current.model_copy(
                            update={
                                "status": "ready",
                                "metadata": {
                                    **(current.metadata or {}),
                                    "quality_assured": True,
                                    "repair_attempts": attempts,
                                },
                            }
                        )
                    )
                    report = self._build_report(
                        project_id=project_id,
                        script=approved,
                        outline=current_outline,
                        repair_attempts=attempts,
                        final_status="approved",
                        validation_status="pass",
                        findings=findings,
                        errors=[],
                        warnings=warnings,
                        empty_sections=empty,
                        missing_sections=missing,
                    )
                    self._persist(
                        project_id,
                        approved=approved,
                        report=report,
                        repair_log=RepairLog(
                            project_id=project_id,
                            script_id=approved.script_id,
                            entries=repair_entries,
                            created_at=utc_now_iso(),
                        ),
                    )
                    logger.info(
                        "EducationalScript approved by QA",
                        extra={
                            "event": "script_quality_approved",
                            "project_id": project_id,
                            "script_id": approved.script_id,
                            "repair_attempts": attempts,
                            "total_words": report.total_words,
                        },
                    )
                    return approved

            if attempts >= MAX_REPAIR_ATTEMPTS or unrecoverable or not actionable:
                report = self._build_report(
                    project_id=project_id,
                    script=current,
                    outline=current_outline,
                    repair_attempts=attempts,
                    final_status="rejected",
                    validation_status="fail",
                    findings=findings,
                    errors=errors or ["Quality assurance failed."],
                    warnings=warnings,
                    empty_sections=empty,
                    missing_sections=missing,
                )
                self._store.write_report(project_id, report)
                self._store.write_repair_log(
                    project_id,
                    RepairLog(
                        project_id=project_id,
                        script_id=current.script_id,
                        entries=repair_entries,
                        created_at=utc_now_iso(),
                    ),
                )
                raise ValidationAppError(
                    "EducationalScript failed quality assurance after repair attempts.",
                    code="SCRIPT_QUALITY_FAILED",
                    details={
                        "project_id": project_id,
                        "script_id": current.script_id,
                        "repair_attempts": attempts,
                        "errors": report.errors,
                        "warnings": report.warnings,
                        "total_words": report.total_words,
                        "estimated_duration_sec": report.estimated_duration_sec,
                        "final_status": report.final_status,
                    },
                )

            attempts += 1
            logger.info(
                "Repairing EducationalScript",
                extra={
                    "event": "script_quality_repair",
                    "project_id": project_id,
                    "attempt": attempts,
                    "mode": "narration_rebuild" if script_rebuilder else "section",
                },
            )
            with timed_step(f"Repair {attempts}"):
                if script_rebuilder is not None:
                    rebuilt, refreshed_outline = script_rebuilder(
                        current, actionable, attempts
                    )
                    current = enrich_script_with_metrics(rebuilt)
                    if refreshed_outline is not None:
                        current_outline = refreshed_outline
                    repair_entries.append(
                        RepairLogEntry(
                            attempt=attempts,
                            section_id="narration",
                            action=RepairAction.EXPAND,
                            before_words=count_words(
                                " ".join(s.narration for s in script.teaching_sections)
                            ),
                            after_words=current.estimated_word_count,
                            notes="Regenerated continuous narration and rebuilt scenes.",
                        )
                    )
                else:
                    requests = self._repair.build_requests(
                        current,
                        actionable,
                        outline=current_outline,
                        attempt=attempts,
                    )
                    if not requests:
                        report = self._build_report(
                            project_id=project_id,
                            script=current,
                            outline=current_outline,
                            repair_attempts=attempts,
                            final_status="rejected",
                            validation_status="fail",
                            findings=findings,
                            errors=errors or ["No actionable repair requests."],
                            warnings=warnings,
                            empty_sections=empty,
                            missing_sections=missing,
                        )
                        self._store.write_report(project_id, report)
                        raise ValidationAppError(
                            "EducationalScript failed quality assurance (no repair actions).",
                            code="SCRIPT_QUALITY_FAILED",
                            details={
                                "project_id": project_id,
                                "errors": report.errors,
                                "repair_attempts": attempts,
                            },
                        )
                    current, new_entries = self._repair.repair(
                        current, requests, attempt=attempts
                    )
                    repair_entries.extend(new_entries)
                    current = enrich_script_with_metrics(current)

    def _build_report(
        self,
        *,
        project_id: str,
        script: EducationalScript,
        outline: TeachingOutline | None,
        repair_attempts: int,
        final_status: FinalStatus,
        validation_status: ValidationStatus,
        findings: list[QualityFinding] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        empty_sections: list[str] | None = None,
        missing_sections: list[str] | None = None,
    ) -> QualityReport:
        if findings is None:
            findings, errors, warnings, empty_sections, missing_sections = (
                self._inspector.inspect(script, outline=outline)
            )
        metrics = self._calculator.compute(script)
        return QualityReport(
            project_id=project_id,
            script_id=script.script_id,
            validation_status=validation_status,
            repair_attempts=repair_attempts,
            total_words=metrics.total_words,
            estimated_duration_sec=metrics.estimated_duration_sec,
            readability_score=readability_score_from_level(metrics.reading_level),
            repeated_concepts=self._inspector.repeated_concepts(script),
            empty_sections=list(empty_sections or []),
            missing_sections=list(missing_sections or []),
            warnings=list(warnings or []),
            errors=list(errors or []),
            findings=list(findings or []),
            final_status=final_status,
            created_at=utc_now_iso(),
            metadata={"reading_level": metrics.reading_level},
        )

    def _persist(
        self,
        project_id: str,
        *,
        approved: EducationalScript,
        report: QualityReport,
        repair_log: RepairLog,
    ) -> None:
        self._store.write_report(project_id, report)
        self._store.write_approved(project_id, approved)
        self._store.write_repair_log(project_id, repair_log)
