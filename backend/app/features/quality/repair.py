"""ScriptRepairService — repair affected teaching sections only (Phase 3.9)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.outline.schemas import TeachingOutline
from app.features.outline.schemas import TeachingSection as OutlineTeachingSection
from app.features.quality.factory import create_repair_generator
from app.features.quality.inspector import QualityInspector
from app.features.quality.protocols import RepairGenerator
from app.features.quality.schemas import (
    QualityFinding,
    RepairAction,
    RepairLogEntry,
    SectionRepairRequest,
)
from app.features.script.metrics import count_words, enrich_script_with_metrics
from app.features.script.schemas import EducationalScript, TeachingSection
from app.features.section_generation.schemas import SectionOutput

logger = get_logger(__name__)


def _short_summary(narration: str) -> str:
    words = narration.split()
    if len(words) <= 28:
        return narration.strip()
    return " ".join(words[:28]) + "…"


def infer_section_repair_action(
    errors: list[str],
    *,
    actual_words: int,
    target_words: int,
) -> RepairAction:
    """Choose a targeted repair action from section validation errors."""
    joined = " ".join(errors).lower()
    if "word count" in joined or "outside the allowed band" in joined:
        if actual_words < max(target_words, 1):
            return RepairAction.EXPAND
        return RepairAction.SHORTEN
    if "unspeakable" in joined:
        return RepairAction.SIMPLIFY
    if "non-empty" in joined or "at least one word" in joined:
        return RepairAction.EXPAND
    if "summary" in joined:
        return RepairAction.IMPROVE_TRANSITIONS
    return RepairAction.SIMPLIFY


class ScriptRepairService:
    """Apply targeted repairs to failing sections — never regenerate the whole script."""

    def __init__(
        self,
        settings: Settings,
        *,
        generator: RepairGenerator | None = None,
        inspector: QualityInspector | None = None,
    ) -> None:
        self._generator = generator or create_repair_generator(settings)
        self._inspector = inspector or QualityInspector()

    def build_requests(
        self,
        script: EducationalScript,
        findings: list[QualityFinding],
        *,
        outline: TeachingOutline | None = None,
        attempt: int,
    ) -> list[SectionRepairRequest]:
        """Map findings to unique per-section repair requests."""
        by_section: dict[str, QualityFinding] = {}
        for finding in findings:
            if finding.section_id is None or finding.repair_action is None:
                continue
            # Prefer expand/shorten over softer actions when both apply.
            existing = by_section.get(finding.section_id)
            if existing is None:
                by_section[finding.section_id] = finding
            elif finding.repair_action in {RepairAction.EXPAND, RepairAction.SHORTEN}:
                by_section[finding.section_id] = finding

        total_words = sum(count_words(s.narration) for s in script.teaching_sections)
        from app.features.script.durations import V1_MIN_WORDS, V1_TARGET_WORDS_MIN

        words_needed = max(0, V1_TARGET_WORDS_MIN - total_words)
        expand_ids = [
            sid
            for sid, finding in by_section.items()
            if finding.repair_action == RepairAction.EXPAND
        ]

        sections = {s.id: (i, s) for i, s in enumerate(script.teaching_sections)}
        requests: list[SectionRepairRequest] = []
        for section_id, finding in by_section.items():
            indexed = sections.get(section_id)
            if indexed is None:
                continue
            index, section = indexed
            objective = ""
            actual_words = count_words(section.narration)
            target_words = max(actual_words, 20)
            if outline is not None:
                for outline_section in outline.sections:
                    if outline_section.id == section_id:
                        objective = outline_section.learning_objective
                        target_words = max(target_words, outline_section.target_words)
                        break

            if finding.repair_action == RepairAction.EXPAND:
                share = max(25, (words_needed // max(len(expand_ids), 1)) + 10)
                target_words = max(
                    target_words,
                    actual_words + share,
                    35,
                )
                # Later attempts push harder toward the V1 band.
                if attempt >= 2:
                    target_words = max(
                        target_words,
                        int(V1_MIN_WORDS / max(len(script.teaching_sections), 1)) + 5,
                    )
            elif finding.repair_action == RepairAction.SHORTEN:
                target_words = max(12, min(target_words, int(actual_words * 0.75)))

            prev_summary = ""
            if index > 0:
                prev = script.teaching_sections[index - 1].narration
                words = prev.split()
                prev_summary = " ".join(words[:24]) + ("…" if len(words) > 24 else "")
            next_title = (
                script.teaching_sections[index + 1].title
                if index + 1 < len(script.teaching_sections)
                else None
            )
            requests.append(
                SectionRepairRequest(
                    section_id=section_id,
                    action=finding.repair_action,
                    validation_failures=[finding.message],
                    target_words=target_words,
                    actual_words=actual_words,
                    learning_objective=objective,
                    previous_section_summary=prev_summary,
                    next_section_title=next_title,
                    original_narration=section.narration,
                    original_title=section.title,
                )
            )
        return requests

    def repair_section_output(
        self,
        output: SectionOutput,
        *,
        expected: OutlineTeachingSection,
        validation_errors: list[str],
        previous_section_summary: str,
        next_section_title: str | None,
        attempt: int,
    ) -> SectionOutput:
        """Repair one SectionOutput in place — never regenerates other sections."""
        actual_words = count_words(output.narration)
        target_words = max(expected.target_words, 1)
        action = infer_section_repair_action(
            validation_errors,
            actual_words=actual_words,
            target_words=target_words,
        )
        request = SectionRepairRequest(
            section_id=output.outline_section_id,
            action=action,
            validation_failures=list(validation_errors),
            target_words=target_words,
            actual_words=actual_words,
            learning_objective=expected.learning_objective or output.learning_objective,
            previous_section_summary=previous_section_summary,
            next_section_title=next_section_title,
            original_narration=output.narration,
            original_title=output.title,
        )
        repaired_text = self._generator.repair_section(request).strip()
        if not repaired_text:
            repaired_text = output.narration

        after_words = count_words(repaired_text)
        metadata = dict(output.metadata)
        metadata["actual_words"] = after_words
        metadata["repair_attempt"] = attempt
        metadata["repair_action"] = action.value

        logger.info(
            "Section output repaired",
            extra={
                "event": "section_output_repaired",
                "section_id": output.outline_section_id,
                "action": action.value,
                "attempt": attempt,
                "before_words": actual_words,
                "after_words": after_words,
                "target_words": target_words,
            },
        )
        return output.model_copy(
            update={
                "narration": repaired_text,
                "summary": _short_summary(repaired_text),
                "metadata": metadata,
            }
        )

    def repair(
        self,
        script: EducationalScript,
        requests: list[SectionRepairRequest],
        *,
        attempt: int,
    ) -> tuple[EducationalScript, list[RepairLogEntry]]:
        if not requests:
            return script, []

        by_id = {s.id: s for s in script.teaching_sections}
        entries: list[RepairLogEntry] = []
        for request in requests:
            section = by_id.get(request.section_id)
            if section is None:
                continue
            before = count_words(section.narration)
            repaired_text = self._generator.repair_section(request).strip()
            if not repaired_text:
                continue
            by_id[request.section_id] = section.model_copy(
                update={"narration": repaired_text}
            )
            after = count_words(repaired_text)
            entries.append(
                RepairLogEntry(
                    attempt=attempt,
                    section_id=request.section_id,
                    action=request.action,
                    before_words=before,
                    after_words=after,
                    notes=f"Applied {request.action.value}",
                )
            )
            logger.info(
                "Teaching section repaired",
                extra={
                    "event": "script_section_repaired",
                    "script_id": script.script_id,
                    "section_id": request.section_id,
                    "action": request.action.value,
                    "attempt": attempt,
                    "before_words": before,
                    "after_words": after,
                },
            )

        new_sections: list[TeachingSection] = [
            by_id[s.id] for s in script.teaching_sections
        ]
        updated = script.model_copy(update={"teaching_sections": new_sections})
        # Always recalculate metrics after repair — never fake numbers.
        return enrich_script_with_metrics(updated), entries
