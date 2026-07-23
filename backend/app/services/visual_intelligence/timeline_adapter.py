"""Adapt a ScenePlan into the scene-JSON interface the Timeline Engine reads.

The Timeline Engine (``animation.TimelineEngine.build_from_scene``) consumes a
scene dictionary with ``scene_id``, ``title``, ``duration``, ``camera`` and an
optional ``timeline.elements`` list; it ignores unknown keys. This adapter maps
a :class:`ScenePlan` onto exactly that shape so downstream animation works
unchanged — it performs *input-interface adaptation only* and never imports or
modifies the Timeline Engine.

Each visual layer becomes one timeline element so the engine can animate layers
independently while remaining fully backward compatible.
"""

from __future__ import annotations

from typing import Any

from app.services.visual_intelligence.schemas import Complexity, LayerType

# Layer → the Timeline Engine's component_type vocabulary.
_LAYER_COMPONENT_TYPE: dict[LayerType, str] = {
    LayerType.BACKGROUND: "background",
    LayerType.FOREGROUND: "asset",
    LayerType.DIAGRAM: "diagram",
    LayerType.OVERLAY: "asset",
    LayerType.LABELS: "text",
    LayerType.ICONS: "icon",
    LayerType.EFFECTS: "effect",
}

# Complexity → gentle cinematic zoom (kept within the 1.00–1.10 clamp the
# rendering camera enforces; heavier scenes get slightly more push-in).
_COMPLEXITY_ZOOM: dict[Complexity, float] = {
    Complexity.TRIVIAL: 1.02,
    Complexity.SIMPLE: 1.04,
    Complexity.MODERATE: 1.07,
    Complexity.COMPLEX: 1.10,
}


def scene_plan_to_timeline_scene(plan: Any) -> dict[str, Any]:
    """Convert one ScenePlan into a Timeline-Engine-ready scene dict.

    ``plan`` is a
    :class:`app.services.visual_intelligence.service.ScenePlan` (imported lazily
    via duck typing to avoid a circular import).
    """
    intent = plan.intent
    strategy = plan.strategy
    layered = plan.layered_scene

    duration = float(intent.estimated_duration or layered.duration_sec or 5.0)
    ordered_layers = layered.ordered()
    legacy = layered.to_legacy_dict()

    elements: list[dict[str, Any]] = []
    reveal_window = duration * 0.6
    step = reveal_window / len(ordered_layers) if ordered_layers else 0.0
    for index, layer in enumerate(ordered_layers):
        anim = layer.animation
        start = anim.start if anim.start > 0 else round(index * step, 3)
        elements.append(
            {
                "component_id": f"{layered.scene_id}:{layer.layer_type.value}",
                "component_type": _LAYER_COMPONENT_TYPE.get(layer.layer_type, "asset"),
                "start_time": round(min(start, max(0.0, duration - 0.5)), 3),
                "z_index": layer.z_index,
                "asset_path": layer.asset_path,
                "opacity": layer.opacity,
                "animation": anim.model_dump(),
            }
        )

    return {
        "scene_id": layered.scene_id,
        "title": (intent.reasoning or "")[:60],
        "duration": duration,
        "camera": {"zoom": _COMPLEXITY_ZOOM.get(intent.complexity, 1.05)},
        "timeline": {"duration": duration, "elements": elements},
        # --- Visual Intelligence metadata (ignored by the Timeline Engine) ---
        "visual_type": intent.visual_type.value,
        "renderer": strategy.primary_renderer.value,
        "fallback_renderers": [r.value for r in strategy.fallback_renderers],
        "complexity": intent.complexity.value,
        "confidence": intent.confidence,
        "layers": legacy["layers"],
        "illustration_path": legacy["illustration_path"],
    }


def scene_plans_to_timeline_scenes(plans: list[Any]) -> list[dict[str, Any]]:
    """Convert many ScenePlans into Timeline-ready scene dicts."""
    return [scene_plan_to_timeline_scene(p) for p in plans]
