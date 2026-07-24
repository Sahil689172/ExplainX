"""Asset Generation models — deterministic educational visual assets."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    """Kind of generated visual asset."""

    FLOWCHART = "flowchart"
    DIAGRAM = "diagram"
    CHART = "chart"
    ICON = "icon"
    BACKGROUND = "background"
    TIMELINE = "timeline"
    INFOGRAPHIC = "infographic"
    SEQUENCE = "sequence"
    STATE = "state"
    ILLUSTRATION = "illustration"
    COMPOSITE = "composite"


class AssetFormat(str, Enum):
    """On-disk format of a generated file."""

    SVG = "svg"
    PNG = "png"
    MMD = "mmd"
    JSON = "json"


class AssetStatus(str, Enum):
    """Lifecycle status of a generated asset."""

    PENDING = "pending"
    GENERATED = "generated"
    CACHED = "cached"
    VALIDATED = "validated"
    FAILED = "failed"
    SKIPPED = "skipped"


class GeneratorType(str, Enum):
    """Registered generator plugins (priority order for selection)."""

    MERMAID = "mermaid"
    SVG = "svg"
    MATPLOTLIB = "matplotlib"
    ICON = "icon"
    BACKGROUND = "background"
    TIMELINE = "timeline"
    INFOGRAPHIC = "infographic"
    LOCAL_IMAGE = "local_image"


# Deterministic-first priority (never AI unless nothing else supports the plan).
GENERATOR_PRIORITY: tuple[GeneratorType, ...] = (
    GeneratorType.MERMAID,
    GeneratorType.SVG,
    GeneratorType.MATPLOTLIB,
    GeneratorType.ICON,
    GeneratorType.BACKGROUND,
    GeneratorType.TIMELINE,
    GeneratorType.INFOGRAPHIC,
    GeneratorType.LOCAL_IMAGE,
)


class AssetMetadata(BaseModel):
    """Sidecar metadata persisted next to generated files."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    generator: GeneratorType
    asset_type: AssetType
    content_hash: str
    style: str = "educational"
    theme: str = "light"
    language: str = "en"
    width: int | None = None
    height: int | None = None
    generation_time_sec: float = 0.0
    cache_hit: bool = False
    source_visual_type: str = ""
    source_renderer: str = ""
    layers: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class GeneratedAsset(BaseModel):
    """One concrete asset file produced for a scene."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    scene_id: str
    asset_type: AssetType
    format: AssetFormat
    path: str
    generator: GeneratorType
    status: AssetStatus = AssetStatus.GENERATED
    content_hash: str = ""
    width: int | None = None
    height: int | None = None
    generation_time_sec: float = 0.0
    cache_hit: bool = False
    metadata: AssetMetadata | None = None


class GenerationResult(BaseModel):
    """Outcome of generating assets for one ScenePlan."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    generator: GeneratorType
    status: AssetStatus
    assets: list[GeneratedAsset] = Field(default_factory=list)
    primary_path: str | None = None
    content_hash: str = ""
    cache_hit: bool = False
    generation_time_sec: float = 0.0
    detail: str = ""
    metadata: AssetMetadata | None = None


class AssetBundle(BaseModel):
    """All assets for one scene after generation + optional composition."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    result: GenerationResult
    composed_path: str | None = None
    layer_paths: dict[str, str] = Field(default_factory=dict)
    export_dir: str = ""


class ScenePackage(BaseModel):
    """Composable package of layered assets ready for downstream rendering."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    background_path: str | None = None
    foreground_path: str | None = None
    diagram_path: str | None = None
    chart_path: str | None = None
    icon_paths: list[str] = Field(default_factory=list)
    label_paths: list[str] = Field(default_factory=list)
    overlay_path: str | None = None
    composed_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
