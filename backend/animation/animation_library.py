"""Reusable animation presets for educational content."""

from __future__ import annotations

from dataclasses import dataclass

from animation.animation_metadata import AnimationType, CameraAnimationType, SceneTransitionType


@dataclass(frozen=True, slots=True)
class AnimationPreset:
    """Maps component types to animation types for a scene style."""

    preset_id: str
    display_name: str
    entry_transition: SceneTransitionType
    exit_transition: SceneTransitionType
    default_camera: CameraAnimationType
    component_animations: dict[str, AnimationType]
    bullet_animation: AnimationType = AnimationType.SEQUENTIAL_REVEAL
    exit_fade: bool = True


PRESETS: dict[str, AnimationPreset] = {
    "educational_diagram": AnimationPreset(
        preset_id="educational_diagram",
        display_name="Educational Diagram",
        entry_transition=SceneTransitionType.CROSSFADE,
        exit_transition=SceneTransitionType.DISSOLVE,
        default_camera=CameraAnimationType.KEN_BURNS,
        component_animations={
            "background": AnimationType.FADE_IN,
            "title": AnimationType.SLIDE_DOWN,
            "subtitle": AnimationType.FADE_IN,
            "diagram": AnimationType.ZOOM_IN,
            "asset": AnimationType.FADE_IN,
            "legend": AnimationType.FADE_IN,
            "caption": AnimationType.FADE_IN,
            "footer": AnimationType.FADE_IN,
        },
    ),
    "concept_reveal": AnimationPreset(
        preset_id="concept_reveal",
        display_name="Concept Reveal",
        entry_transition=SceneTransitionType.FADE_THROUGH_WHITE,
        exit_transition=SceneTransitionType.CROSSFADE,
        default_camera=CameraAnimationType.ZOOM,
        component_animations={
            "title": AnimationType.FADE_IN,
            "diagram": AnimationType.ZOOM_IN,
            "asset": AnimationType.ZOOM_IN,
            "subtitle": AnimationType.SLIDE_UP,
        },
    ),
    "bullet_reveal": AnimationPreset(
        preset_id="bullet_reveal",
        display_name="Bullet Reveal",
        entry_transition=SceneTransitionType.SLIDE,
        exit_transition=SceneTransitionType.SLIDE,
        default_camera=CameraAnimationType.STATIC,
        component_animations={
            "title": AnimationType.SLIDE_LEFT,
            "bullet_list": AnimationType.SEQUENTIAL_REVEAL,
            "diagram": AnimationType.FADE_IN,
        },
        bullet_animation=AnimationType.SEQUENTIAL_REVEAL,
    ),
    "process_flow": AnimationPreset(
        preset_id="process_flow",
        display_name="Process Flow",
        entry_transition=SceneTransitionType.PUSH,
        exit_transition=SceneTransitionType.DISSOLVE,
        default_camera=CameraAnimationType.PAN,
        component_animations={
            "diagram": AnimationType.SLIDE_RIGHT,
            "bullet_list": AnimationType.SEQUENTIAL_REVEAL,
            "legend": AnimationType.DRAW_ARROW,
        },
        bullet_animation=AnimationType.SEQUENTIAL_REVEAL,
    ),
    "comparison": AnimationPreset(
        preset_id="comparison",
        display_name="Comparison",
        entry_transition=SceneTransitionType.SLIDE,
        exit_transition=SceneTransitionType.CROSSFADE,
        default_camera=CameraAnimationType.STATIC,
        component_animations={
            "asset": AnimationType.SLIDE_LEFT,
            "diagram": AnimationType.SLIDE_RIGHT,
            "bullet_list": AnimationType.FADE_IN,
        },
    ),
    "timeline": AnimationPreset(
        preset_id="timeline",
        display_name="Timeline",
        entry_transition=SceneTransitionType.CUT,
        exit_transition=SceneTransitionType.FADE_THROUGH_WHITE,
        default_camera=CameraAnimationType.PAN,
        component_animations={
            "title": AnimationType.FADE_IN,
            "bullet_list": AnimationType.SEQUENTIAL_REVEAL,
            "caption": AnimationType.WRITE_LABEL,
        },
    ),
}


# Topic → preset mapping for demos/tests
TOPIC_PRESETS: dict[str, str] = {
    "earth": "educational_diagram",
    "human heart": "concept_reveal",
    "heart": "concept_reveal",
    "photosynthesis": "process_flow",
    "computer motherboard": "comparison",
    "motherboard": "comparison",
    "solar system": "timeline",
}


def get_preset(preset_id: str | None = None, *, topic: str | None = None) -> AnimationPreset:
    if preset_id and preset_id in PRESETS:
        return PRESETS[preset_id]
    if topic:
        key = topic.strip().lower()
        pid = TOPIC_PRESETS.get(key)
        if pid:
            return PRESETS[pid]
        if "process" in key or "photosynthesis" in key:
            return PRESETS["process_flow"]
        if "comparison" in key or "motherboard" in key:
            return PRESETS["comparison"]
    return PRESETS["educational_diagram"]


def list_presets() -> list[dict[str, str]]:
    return [{"id": p.preset_id, "name": p.display_name} for p in PRESETS.values()]
