"""Pydantic models shared across the Visual Intelligence service."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VisualType(str, Enum):
    """What kind of visual best communicates a scene's idea."""

    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    TIMELINE = "timeline"
    CHART = "chart"
    TABLE = "table"
    MAP = "map"
    MATHEMATICAL = "mathematical"
    SCIENTIFIC = "scientific"
    ILLUSTRATION = "illustration"
    PHOTO = "photo"
    ICON = "icon"
    BACKGROUND = "background"
    TEXT_ONLY = "text_only"
    MIXED = "mixed"


class RendererType(str, Enum):
    """Concrete renderer families the router can select."""

    MERMAID = "mermaid"
    SVG = "svg"
    MATPLOTLIB = "matplotlib"
    MANIM = "manim"
    OPENVINO = "openvino"
    ICON = "icon"
    BACKGROUND = "background"


class Complexity(str, Enum):
    """Rough production complexity — drives duration and cost estimates."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class LayerType(str, Enum):
    """Independent visual layers a composed scene may contain."""

    BACKGROUND = "background"
    FOREGROUND = "foreground"
    DIAGRAM = "diagram"
    OVERLAY = "overlay"
    LABELS = "labels"
    ICONS = "icons"
    EFFECTS = "effects"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


class SceneInput(BaseModel):
    """Everything the analyzer needs to reason about one scene.

    All fields are optional except ``scene_id`` so the model degrades
    gracefully when upstream phases provide partial data.
    """

    model_config = ConfigDict(extra="ignore")

    scene_id: str
    title: str = ""
    narration: str = ""
    keywords: list[str] = Field(default_factory=list)
    educational_concepts: list[str] = Field(default_factory=list)
    learning_objective: str = ""
    duration_hint_sec: float | None = None

    def text_corpus(self) -> str:
        """Concatenated lower-cased text used for keyword matching."""
        parts = [
            self.title,
            self.narration,
            self.learning_objective,
            " ".join(self.keywords),
            " ".join(self.educational_concepts),
        ]
        return " ".join(p for p in parts if p).lower()


# --------------------------------------------------------------------------- #
# Analyzer output
# --------------------------------------------------------------------------- #


class VisualIntent(BaseModel):
    """The analyzer's decision about a scene's ideal visual."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    visual_type: VisualType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggested_renderer: RendererType
    estimated_duration: float = Field(ge=0.0)
    complexity: Complexity
    matched_keywords: list[str] = Field(default_factory=list)
    alternatives: list[VisualType] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Router output
# --------------------------------------------------------------------------- #


class RenderingStrategy(BaseModel):
    """How a :class:`VisualIntent` should be produced (no assets generated)."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    visual_type: VisualType
    primary_renderer: RendererType
    fallback_renderers: list[RendererType] = Field(default_factory=list)
    renderer_options: dict[str, Any] = Field(default_factory=dict)
    layers: list[LayerType] = Field(default_factory=list)
    reasoning: str = ""
    estimated_cost: float = 0.0
    estimated_time_sec: float = 0.0


# --------------------------------------------------------------------------- #
# Cache / repository
# --------------------------------------------------------------------------- #


class RenderRequest(BaseModel):
    """Deterministic description of a render — the cache key source of truth."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = ""
    model: str = ""
    renderer: RendererType
    seed: int | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    def canonical(self) -> str:
        """Stable JSON string used for SHA256 hashing (order-independent)."""
        import json

        payload = {
            "prompt": self.prompt.strip(),
            "model": self.model.strip(),
            "renderer": self.renderer.value,
            "seed": self.seed,
            "parameters": self.parameters,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


class AssetRecord(BaseModel):
    """Metadata persisted alongside every cached asset."""

    model_config = ConfigDict(extra="forbid")

    hash: str
    renderer: RendererType
    prompt: str = ""
    model: str = ""
    seed: int | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    asset_path: str
    svg_path: str | None = None
    thumbnail_path: str | None = None
    metadata_path: str | None = None
    created_at: str
    generation_time_sec: float = 0.0
    width: int | None = None
    height: int | None = None
