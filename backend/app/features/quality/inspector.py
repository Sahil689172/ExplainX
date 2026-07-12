"""Inspect EducationalScript quality without trusting generator metrics."""

from __future__ import annotations

import re
from collections import Counter

from app.features.outline.schemas import TeachingOutline
from app.features.script.durations import (
    V1_MAX_DURATION_SEC,
    V1_MAX_WORDS,
    V1_MIN_DURATION_SEC,
    V1_MIN_WORDS,
)
from app.features.script.metrics import ScriptMetricsCalculator, count_words
from app.features.script.schemas import EducationalScript
from app.features.quality.schemas import QualityFinding, RepairAction

_UNSPEAKABLE = re.compile(r"(```|<html|<table\b)", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}")

# Sections shorter than this are treated as empty / needing expansion.
EMPTY_SECTION_WORD_THRESHOLD = 8


def readability_score_from_level(level: str) -> float:
    return {
        "beginner": 0.85,
        "intermediate": 0.7,
        "advanced": 0.55,
        "unknown": 0.4,
    }.get(level, 0.5)


class QualityInspector:
    """Collect findings for QA pass/repair decisions (never invents metrics)."""

    def __init__(self, *, calculator: ScriptMetricsCalculator | None = None) -> None:
        self._calculator = calculator or ScriptMetricsCalculator()

    def inspect(
        self,
        script: EducationalScript,
        *,
        outline: TeachingOutline | None = None,
    ) -> tuple[list[QualityFinding], list[str], list[str], list[str], list[str]]:
        """Return findings, errors, warnings, empty_sections, missing_sections."""
        findings: list[QualityFinding] = []
        errors: list[str] = []
        warnings: list[str] = []
        empty_sections: list[str] = []
        missing_sections: list[str] = []

        if not script.teaching_sections:
            msg = "EducationalScript must include at least one teaching section."
            errors.append(msg)
            findings.append(
                QualityFinding(
                    code="MISSING_SECTIONS",
                    message=msg,
                    repair_action=None,
                )
            )
            return findings, errors, warnings, empty_sections, missing_sections

        if not script.summary.strip():
            msg = "EducationalScript.summary is required."
            errors.append(msg)
            findings.append(QualityFinding(code="MISSING_SUMMARY", message=msg))

        section_ids = [s.id for s in script.teaching_sections]
        if len(set(section_ids)) != len(section_ids):
            msg = "teaching_sections.id values must be unique."
            errors.append(msg)
            findings.append(QualityFinding(code="DUPLICATE_SECTION_IDS", message=msg))

        for index, section in enumerate(script.teaching_sections):
            words = count_words(section.narration)
            if words <= 0 or words < EMPTY_SECTION_WORD_THRESHOLD:
                empty_sections.append(section.id)
                msg = f"Section '{section.id}' narration is empty or too short."
                errors.append(msg)
                action = (
                    RepairAction.STRENGTHEN_INTRODUCTION
                    if index == 0
                    else RepairAction.IMPROVE_CONCLUSION
                    if index == len(script.teaching_sections) - 1
                    else RepairAction.EXPAND
                )
                findings.append(
                    QualityFinding(
                        code="EMPTY_SECTION",
                        message=msg,
                        section_id=section.id,
                        repair_action=action,
                        details={"words": words},
                    )
                )
            if _UNSPEAKABLE.search(section.narration or ""):
                msg = f"Section '{section.id}' contains unspeakable formatting."
                errors.append(msg)
                findings.append(
                    QualityFinding(
                        code="UNSPEAKABLE",
                        message=msg,
                        section_id=section.id,
                        repair_action=RepairAction.SIMPLIFY,
                    )
                )

        if outline is not None:
            script_ids = {s.id for s in script.teaching_sections}
            for outline_section in outline.sections:
                if outline_section.id not in script_ids:
                    missing_sections.append(outline_section.id)
            if missing_sections:
                msg = f"Script is missing outline sections: {missing_sections}."
                errors.append(msg)
                findings.append(
                    QualityFinding(
                        code="MISSING_OUTLINE_SECTIONS",
                        message=msg,
                        details={"missing_sections": missing_sections},
                    )
                )

        metrics = self._calculator.compute(script)
        if metrics.total_words < V1_MIN_WORDS or metrics.total_duration_sec < V1_MIN_DURATION_SEC:
            msg = (
                f"Script too short ({metrics.total_words} words / "
                f"{metrics.total_duration_sec}s); need ≥{V1_MIN_WORDS} words / "
                f"≥{V1_MIN_DURATION_SEC}s."
            )
            errors.append(msg)
            # Expand the shortest sections first.
            ordered = sorted(
                script.teaching_sections,
                key=lambda s: count_words(s.narration),
            )
            for section in ordered[: max(1, min(3, len(ordered)))]:
                findings.append(
                    QualityFinding(
                        code="TOO_SHORT",
                        message=msg,
                        section_id=section.id,
                        repair_action=RepairAction.EXPAND,
                        details={
                            "total_words": metrics.total_words,
                            "estimated_duration_sec": metrics.total_duration_sec,
                        },
                    )
                )

        if metrics.total_words > V1_MAX_WORDS or metrics.total_duration_sec > V1_MAX_DURATION_SEC:
            msg = (
                f"Script too long ({metrics.total_words} words / "
                f"{metrics.total_duration_sec}s); max {V1_MAX_WORDS} words / "
                f"{V1_MAX_DURATION_SEC}s."
            )
            errors.append(msg)
            ordered = sorted(
                script.teaching_sections,
                key=lambda s: count_words(s.narration),
                reverse=True,
            )
            for section in ordered[: max(1, min(3, len(ordered)))]:
                findings.append(
                    QualityFinding(
                        code="TOO_LONG",
                        message=msg,
                        section_id=section.id,
                        repair_action=RepairAction.SHORTEN,
                        details={
                            "total_words": metrics.total_words,
                            "estimated_duration_sec": metrics.total_duration_sec,
                        },
                    )
                )

        repeated = self._repeated_concepts(script)
        if repeated:
            warnings.append(f"Repeated concepts across sections: {repeated}.")
            for section in script.teaching_sections:
                if any(tag.strip().lower() in repeated for tag in section.concept_tags):
                    findings.append(
                        QualityFinding(
                            code="REPEATED_CONCEPTS",
                            message="Section may repeat concepts already covered.",
                            section_id=section.id,
                            repair_action=RepairAction.REMOVE_REPETITION,
                            details={"repeated_concepts": repeated},
                        )
                    )

        # Soft transition heuristic: consecutive sections sharing many content words.
        for index in range(1, len(script.teaching_sections)):
            prev = script.teaching_sections[index - 1]
            curr = script.teaching_sections[index]
            overlap = self._content_overlap(prev.narration, curr.narration)
            if overlap >= 0.35:
                warnings.append(
                    f"High lexical overlap between '{prev.id}' and '{curr.id}'."
                )
                findings.append(
                    QualityFinding(
                        code="WEAK_TRANSITION",
                        message="Improve transition / reduce overlap with previous section.",
                        section_id=curr.id,
                        repair_action=RepairAction.IMPROVE_TRANSITIONS,
                        details={"overlap": overlap, "previous_section_id": prev.id},
                    )
                )

        return findings, errors, warnings, empty_sections, missing_sections

    def repeated_concepts(self, script: EducationalScript) -> list[str]:
        return self._repeated_concepts(script)

    @staticmethod
    def _repeated_concepts(script: EducationalScript) -> list[str]:
        counter: Counter[str] = Counter()
        for section in script.teaching_sections:
            for tag in section.concept_tags:
                label = tag.strip().lower()
                if label:
                    counter[label] += 1
        return sorted(label for label, count in counter.items() if count >= 3)

    @staticmethod
    def _content_overlap(a: str, b: str) -> float:
        wa = {_normalize_token(t) for t in _WORD_RE.findall(a.lower())}
        wb = {_normalize_token(t) for t in _WORD_RE.findall(b.lower())}
        wa.discard("")
        wb.discard("")
        if not wa or not wb:
            return 0.0
        inter = len(wa & wb)
        return inter / max(1, min(len(wa), len(wb)))


def _normalize_token(token: str) -> str:
    stop = {
        "the",
        "and",
        "for",
        "that",
        "with",
        "this",
        "from",
        "have",
        "will",
        "each",
        "into",
        "about",
        "your",
        "their",
        "when",
        "what",
        "which",
        "while",
        "then",
        "than",
        "also",
        "just",
        "like",
        "over",
        "such",
        "only",
        "other",
        "some",
        "them",
        "they",
        "were",
        "been",
        "being",
        "does",
        "done",
        "make",
        "made",
        "more",
        "most",
        "very",
        "into",
        "onto",
        "our",
        "out",
        "can",
        "could",
        "should",
        "would",
        "section",
        "lesson",
        "learner",
        "learners",
        "explanation",
        "idea",
        "ideas",
        "point",
        "points",
    }
    cleaned = token.strip().lower()
    return "" if cleaned in stop else cleaned
