"""Validate PresentationPlan invariants before persistence."""

from __future__ import annotations

from app.core.errors import ValidationAppError
from app.features.input.schemas import RawContent
from app.features.presentation.schemas import PresentationPlan


class PresentationPlanValidator:
    def validate(self, plan: PresentationPlan, *, raw: RawContent | None = None) -> None:
        if not plan.teaching_sections:
            raise ValidationAppError(
                "PresentationPlan must include at least one teaching section.",
                code="PLAN_VALIDATION_ERROR",
                details={"field": "teaching_sections"},
            )

        orders = [s.order for s in plan.teaching_sections]
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ValidationAppError(
                "teaching_sections.order must be contiguous starting at 1.",
                code="PLAN_VALIDATION_ERROR",
                details={"orders": orders},
            )

        concept_ids = {c.id for c in plan.key_concepts}
        objective_ids = {o.id for o in plan.learning_objectives}
        visual_ids = {v.id for v in plan.visual_candidates}

        for section in plan.teaching_sections:
            unknown_concepts = [i for i in section.concept_ids if i not in concept_ids]
            if unknown_concepts:
                raise ValidationAppError(
                    "teaching section references unknown concept ids.",
                    code="PLAN_VALIDATION_ERROR",
                    details={"section_id": section.id, "concept_ids": unknown_concepts},
                )
            unknown_objectives = [i for i in section.objective_ids if i not in objective_ids]
            if unknown_objectives:
                raise ValidationAppError(
                    "teaching section references unknown objective ids.",
                    code="PLAN_VALIDATION_ERROR",
                    details={"section_id": section.id, "objective_ids": unknown_objectives},
                )
            unknown_visuals = [i for i in section.visual_candidate_ids if i not in visual_ids]
            if unknown_visuals:
                raise ValidationAppError(
                    "teaching section references unknown visual candidate ids.",
                    code="PLAN_VALIDATION_ERROR",
                    details={"section_id": section.id, "visual_candidate_ids": unknown_visuals},
                )

        if raw is not None and plan.content_id != raw.content_id:
            raise ValidationAppError(
                "PresentationPlan.content_id must match RawContent.content_id.",
                code="PLAN_VALIDATION_ERROR",
                details={
                    "plan_content_id": plan.content_id,
                    "raw_content_id": raw.content_id,
                },
            )

        if plan.estimated_duration_sec < 0:
            raise ValidationAppError(
                "estimated_duration_sec must be non-negative.",
                code="PLAN_VALIDATION_ERROR",
                details={"estimated_duration_sec": plan.estimated_duration_sec},
            )
