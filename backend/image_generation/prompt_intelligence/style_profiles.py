"""Style profiles for educational illustration generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StyleProfile:
    """Visual HOW profile — independent of subject WHAT."""

    style_id: str
    display_name: str
    prompt_clause: str


STYLE_PROFILES: dict[str, StyleProfile] = {
    "flat_vector": StyleProfile(
        style_id="flat_vector",
        display_name="Flat Vector Educational",
        prompt_clause="flat vector educational illustration",
    ),
    "educational_diagram": StyleProfile(
        style_id="educational_diagram",
        display_name="Educational Diagram",
        prompt_clause="clean educational diagram style",
    ),
    "textbook_illustration": StyleProfile(
        style_id="textbook_illustration",
        display_name="Textbook Illustration",
        prompt_clause="science textbook illustration style",
    ),
    "minimal_icon": StyleProfile(
        style_id="minimal_icon",
        display_name="Minimal Icon",
        prompt_clause="minimal vector icon style",
    ),
    "infographic": StyleProfile(
        style_id="infographic",
        display_name="Infographic",
        prompt_clause="simple educational infographic style",
    ),
    "whiteboard_sketch": StyleProfile(
        style_id="whiteboard_sketch",
        display_name="Whiteboard Sketch",
        prompt_clause="whiteboard marker sketch style",
    ),
    "scientific_illustration": StyleProfile(
        style_id="scientific_illustration",
        display_name="Scientific Illustration",
        prompt_clause="scientific illustration style",
    ),
    "simple_cartoon": StyleProfile(
        style_id="simple_cartoon",
        display_name="Simple Cartoon",
        prompt_clause="simple friendly educational cartoon style",
    ),
}

DEFAULT_STYLE_ID = "flat_vector"


def get_style(style_id: str | None) -> StyleProfile:
    if not style_id:
        return STYLE_PROFILES[DEFAULT_STYLE_ID]
    key = style_id.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "flat": "flat_vector",
        "flat_vector_educational": "flat_vector",
        "diagram": "educational_diagram",
        "textbook": "textbook_illustration",
        "icon": "minimal_icon",
        "whiteboard": "whiteboard_sketch",
        "scientific": "scientific_illustration",
        "cartoon": "simple_cartoon",
    }
    key = aliases.get(key, key)
    return STYLE_PROFILES.get(key, STYLE_PROFILES[DEFAULT_STYLE_ID])
