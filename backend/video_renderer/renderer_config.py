"""Renderer configuration for Phase 6.0."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RendererConfig:
    """Canvas and output settings."""

    width: int = 1280
    height: int = 720
    fps: int = 30
    background: tuple[int, int, int, int] = (255, 255, 252, 255)
    margin: float = 48.0


# Topic hints when scene JSON lacks bullet content (no Scene Composer changes).
TOPIC_BULLETS: dict[str, list[str]] = {
    "earth": ["Core", "Mantle", "Crust"],
    "planet earth": ["Core", "Mantle", "Crust"],
    "human heart": ["Left atrium", "Right ventricle", "Valves"],
    "heart": ["Left atrium", "Right ventricle", "Valves"],
    "photosynthesis": ["Sunlight", "Water + CO₂", "Oxygen output"],
    "computer motherboard": ["CPU socket", "RAM slots", "PCIe"],
    "motherboard": ["CPU socket", "RAM slots", "PCIe"],
    "solar system": ["Sun", "Inner planets", "Outer planets"],
}

TOPIC_SUBTITLES: dict[str, str] = {
    "earth": "Structure of our planet",
    "human heart": "Chambers and blood flow",
    "photosynthesis": "Energy conversion in plants",
    "computer motherboard": "Main board components",
    "solar system": "Planets orbiting the Sun",
}

DEFAULT_FOOTER = "ExplainX Educational Scene"

Z_INDEX: dict[str, int] = {
    "background": 0,
    "title": 10,
    "subtitle": 20,
    "asset": 30,
    "diagram": 40,
    "bullet_list": 50,
    "legend": 60,
    "caption": 70,
    "footer": 80,
}
