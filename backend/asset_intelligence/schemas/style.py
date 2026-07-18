"""Style system schemas — HOW, never WHAT."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from asset_intelligence.schemas.version import SCHEMA_VERSION


@dataclass(slots=True)
class StyleProfile:
    """Independent visual style profile (loaded from JSON, not hardcoded prompts)."""

    style_id: str
    display_name: str
    positive_prompt: str
    negative_prompt: str
    color_palette: list[str] = field(default_factory=list)
    line_weight: str = "medium"  # thin | medium | bold
    lighting: str = "flat"
    background_rules: str = "plain solid or transparent as appropriate"
    renderer_preferences: dict[str, Any] = field(default_factory=dict)
    lora_mapping: dict[str, Any] = field(default_factory=dict)
    controlnet_mapping: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
