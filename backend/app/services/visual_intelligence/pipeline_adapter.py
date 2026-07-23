"""Adapter exposing Visual Intelligence to the existing pipeline (additive).

The upstream Content Intelligence phase emits an ``EducationalScript`` with
``teaching_sections``. This adapter converts those sections into
:class:`SceneInput` objects and returns per-scene plans, without importing or
modifying any completed phase. It uses duck typing (works with the Pydantic
model or a plain dict), so there is no hard dependency on the script package.
"""

from __future__ import annotations

from typing import Any

from app.services.visual_intelligence.schemas import SceneInput
from app.services.visual_intelligence.service import ScenePlan, VisualIntelligenceService


def _get(obj: Any, name: str, default: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def script_to_scene_inputs(script: Any) -> list[SceneInput]:
    """Convert an EducationalScript (model or dict) into SceneInputs.

    Recognized fields: ``teaching_sections`` (each with ``id``, ``title``,
    ``narration``, ``concept_tags``, ``estimated_duration_sec``),
    ``learning_objectives``, and top-level ``key_concepts``.
    """
    sections = _get(script, "teaching_sections", []) or []
    objectives = _get(script, "learning_objectives", []) or []

    scenes: list[SceneInput] = []
    for index, section in enumerate(sections):
        title = _get(section, "title", "") or ""
        concept_tags = list(_get(section, "concept_tags", []) or [])
        duration = _get(section, "estimated_duration_sec", None)
        # Pair each section with an objective when counts line up.
        objective = objectives[index] if index < len(objectives) else ""
        scenes.append(
            SceneInput(
                scene_id=str(_get(section, "id", f"scene-{index + 1}")),
                title=title,
                narration=_get(section, "narration", "") or "",
                keywords=concept_tags,
                educational_concepts=concept_tags,
                learning_objective=objective or (f"Explain {title}" if title else ""),
                duration_hint_sec=float(duration) if duration else None,
            )
        )
    return scenes


def plan_script(
    script: Any,
    *,
    service: VisualIntelligenceService | None = None,
) -> list[ScenePlan]:
    """One call to plan visuals for an entire EducationalScript."""
    svc = service or VisualIntelligenceService()
    return svc.plan_scenes(script_to_scene_inputs(script))


def plan_script_as_dicts(
    script: Any,
    *,
    service: VisualIntelligenceService | None = None,
) -> list[dict[str, Any]]:
    """Plan an entire script and return JSON-ready, legacy-compatible dicts."""
    return [plan.to_dict() for plan in plan_script(script, service=service)]
