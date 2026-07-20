"""Scene metadata schemas for Phase 5.8 Educational Scene Composer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from image_generation.diagram_composer.geometry import Point, Rect


class SceneType(str, Enum):
    SINGLE_CONCEPT = "single_concept"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    PROCESS = "process"
    STEP_BY_STEP = "step_by_step"
    FLOW = "flow"
    ARCHITECTURE = "architecture"
    CYCLE = "cycle"
    SPLIT_VIEW = "split_view"
    QUESTION_ANSWER = "question_answer"


class SceneLayout(str, Enum):
    CENTERED = "centered"
    TWO_COLUMN = "two_column"
    THREE_COLUMN = "three_column"
    GRID = "grid"
    HERO = "hero"
    LEFT_ILLUSTRATION = "left_illustration"
    RIGHT_ILLUSTRATION = "right_illustration"
    COMPARISON = "comparison"


class ComponentType(str, Enum):
    BACKGROUND = "background"
    TITLE = "title"
    SUBTITLE = "subtitle"
    ASSET = "asset"
    DIAGRAM = "diagram"
    BULLET_LIST = "bullet_list"
    CAPTION = "caption"
    LEGEND = "legend"
    HIGHLIGHT_BOX = "highlight_box"
    CALLOUT = "callout"
    FOOTER = "footer"


@dataclass(slots=True)
class SceneComponent:
    """Logical scene element before layout."""

    component_id: str
    component_type: ComponentType
    content: str = ""
    image_path: str | None = None
    bullets: list[str] = field(default_factory=list)
    concept_id: str | None = None
    asset_version: str | None = None
    diagram_version: str | None = None
    z_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlacedComponent:
    """Scene element after layout with screen bounds."""

    component: SceneComponent
    bounds: Rect
    position: Point


@dataclass(slots=True)
class SceneSpec:
    """Input specification for composing one educational scene."""

    topic: str
    title: str
    subject: str = "General"
    scene_type: SceneType = SceneType.SINGLE_CONCEPT
    layout: SceneLayout = SceneLayout.CENTERED
    subtitle: str | None = None
    caption: str | None = None
    footer: str | None = None
    bullets: list[str] = field(default_factory=list)
    asset_path: str | None = None
    diagram_path: str | None = None
    illustration_path: str | None = None
    concept_id: str | None = None
    asset_version: str | None = None
    diagram_version: str | None = None
    scene_number: int = 1
    duration_seconds: float = 5.0
    width: int = 1280
    height: int = 720
    theme: str = "textbook"
    template_id: str | None = None


@dataclass(slots=True)
class SceneMetadata:
    """Persisted scene metadata for repository / video pipeline."""

    scene_id: str
    scene_number: int
    title: str
    subject: str
    scene_type: str
    layout: str
    assets: list[dict[str, Any]]
    diagrams: list[dict[str, Any]]
    camera: dict[str, Any]
    timeline: dict[str, Any]
    duration: float
    concept_id: str | None = None
    asset_version: str | None = None
    diagram_version: str | None = None
    created_at: str = ""
    export_format: str = "png,svg,json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def create(
        *,
        spec: SceneSpec,
        placed: list[PlacedComponent],
        camera: dict[str, Any],
        timeline: dict[str, Any],
        export_format: str = "png,svg,json",
    ) -> SceneMetadata:
        assets = [
            {
                "component_id": p.component.component_id,
                "type": p.component.component_type.value,
                "path": p.component.image_path,
                "bounds": {
                    "x": p.bounds.x,
                    "y": p.bounds.y,
                    "width": p.bounds.width,
                    "height": p.bounds.height,
                },
                "concept_id": p.component.concept_id,
                "asset_version": p.component.asset_version,
            }
            for p in placed
            if p.component.component_type in (ComponentType.ASSET, ComponentType.DIAGRAM)
        ]
        diagrams = [
            a for a in assets if a["type"] == ComponentType.DIAGRAM.value
        ]
        return SceneMetadata(
            scene_id=str(uuid4()),
            scene_number=spec.scene_number,
            title=spec.title,
            subject=spec.subject,
            scene_type=spec.scene_type.value,
            layout=spec.layout.value,
            assets=assets,
            diagrams=diagrams,
            camera=camera,
            timeline=timeline,
            duration=spec.duration_seconds,
            concept_id=spec.concept_id,
            asset_version=spec.asset_version,
            diagram_version=spec.diagram_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            export_format=export_format,
        )


@dataclass(slots=True)
class SceneResult:
    """Output of a compose + render pass."""

    metadata: SceneMetadata
    placed: list[PlacedComponent]
    png_path: str | None = None
    svg_path: str | None = None
    json_path: str | None = None
