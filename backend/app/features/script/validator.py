"""Validate EducationalScript invariants before persistence."""

from __future__ import annotations

import re

from app.core.errors import ValidationAppError
from app.features.input.schemas import RawContent
from app.features.script.schemas import EducationalScript

_UNSPEAKABLE = re.compile(r"(```|<html|<table\b)", re.IGNORECASE)


class ScriptValidator:
    def validate(self, script: EducationalScript, *, raw: RawContent | None = None) -> None:
        if not script.sections:
            raise ValidationAppError(
                "EducationalScript must include at least one section.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "sections"},
            )
        if not script.beats:
            raise ValidationAppError(
                "EducationalScript must include at least one beat.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "beats"},
            )

        section_orders = [s.order for s in script.sections]
        if sorted(section_orders) != list(range(1, len(section_orders) + 1)):
            raise ValidationAppError(
                "sections.order must be contiguous starting at 1.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"orders": section_orders},
            )

        beat_orders = [b.order for b in script.beats]
        if sorted(beat_orders) != list(range(1, len(beat_orders) + 1)):
            raise ValidationAppError(
                "beats.order must be contiguous starting at 1.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"orders": beat_orders},
            )

        beat_ids = {b.id for b in script.beats}
        if len(beat_ids) != len(script.beats):
            raise ValidationAppError(
                "beat ids must be unique.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"field": "beats.id"},
            )

        section_ids = {s.id for s in script.sections}
        concept_ids = {c.id for c in script.key_concepts}

        for beat in script.beats:
            if beat.section_id not in section_ids:
                raise ValidationAppError(
                    "beat references unknown section_id.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"beat_id": beat.id, "section_id": beat.section_id},
                )
            unknown = [i for i in beat.concept_ids if i not in concept_ids]
            if unknown:
                raise ValidationAppError(
                    "beat references unknown concept ids.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"beat_id": beat.id, "concept_ids": unknown},
                )
            if _UNSPEAKABLE.search(beat.text):
                raise ValidationAppError(
                    "beat text contains unspeakable formatting.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"beat_id": beat.id},
                )

        for section in script.sections:
            missing_beats = [i for i in section.beat_ids if i not in beat_ids]
            if missing_beats:
                raise ValidationAppError(
                    "section references unknown beat ids.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"section_id": section.id, "beat_ids": missing_beats},
                )
            unknown = [i for i in section.concept_ids if i not in concept_ids]
            if unknown:
                raise ValidationAppError(
                    "section references unknown concept ids.",
                    code="SCRIPT_VALIDATION_ERROR",
                    details={"section_id": section.id, "concept_ids": unknown},
                )

        assigned = [b.id for b in script.beats]
        referenced = [bid for s in script.sections for bid in s.beat_ids]
        if sorted(assigned) != sorted(referenced):
            raise ValidationAppError(
                "every beat must be referenced by exactly its section beat_ids.",
                code="SCRIPT_VALIDATION_ERROR",
                details={"beats": assigned, "referenced": referenced},
            )

        if raw is not None and script.content_id != raw.content_id:
            raise ValidationAppError(
                "EducationalScript.content_id must match RawContent.content_id.",
                code="SCRIPT_VALIDATION_ERROR",
                details={
                    "script_content_id": script.content_id,
                    "raw_content_id": raw.content_id,
                },
            )
