"""Prompt Generator — WHAT (concept) + HOW (style). No scenes, no models."""

from __future__ import annotations

from typing import Sequence

from asset_intelligence.schemas.planner import AssetDecision, PlannerDecisionKind
from asset_intelligence.schemas.prompt import PromptBundle
from asset_intelligence.schemas.style import StyleProfile


class PromptGenerator:
    """Builds prompt bundles only for GENERATE decisions.

    Receives planner decisions + style profiles — never raw scenes.
    """

    def generate(self, decision: AssetDecision, style: StyleProfile) -> PromptBundle:
        if decision.kind != PlannerDecisionKind.GENERATE:
            raise ValueError(
                f"PromptGenerator only handles GENERATE; got {decision.kind.value}"
            )
        if style.style_id != decision.requirement.style_id:
            raise ValueError(
                f"Style mismatch: decision wants {decision.requirement.style_id!r}, "
                f"got {style.style_id!r}"
            )

        what = self._what_clause(decision)
        positive = f"{what}, {style.positive_prompt}".strip(", ")
        negative = style.negative_prompt.strip()

        return PromptBundle(
            requirement=decision.requirement,
            style=style,
            positive_prompt=positive,
            negative_prompt=negative,
            metadata={
                "what": what,
                "how_style_id": style.style_id,
                "lighting": style.lighting,
                "line_weight": style.line_weight,
                "background_rules": style.background_rules,
            },
        )

    def generate_many(
        self, decisions: Sequence[AssetDecision], style: StyleProfile
    ) -> Sequence[PromptBundle]:
        return [
            self.generate(d, style)
            for d in decisions
            if d.kind == PlannerDecisionKind.GENERATE
        ]

    @staticmethod
    def _what_clause(decision: AssetDecision) -> str:
        req = decision.requirement
        concept = req.concept.name
        view = req.ontology.view.value if req.ontology.view else "front"
        category = req.ontology.category.value
        parts = [f"educational illustration of {concept}"]
        parts.append(f"category {category}")
        parts.append(f"{view} view")
        if req.ontology.subject:
            parts.append(f"subject {req.ontology.subject}")
        return ", ".join(parts)
