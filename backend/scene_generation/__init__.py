"""Phase 5.8 — Educational Scene Composer."""

from scene_generation.camera import CameraEvent, CameraPlanner, CameraState
from scene_generation.scene_builder import SceneBuilder
from scene_generation.scene_engine import SceneEngine
from scene_generation.scene_layout import SceneLayoutEngine
from scene_generation.scene_metadata import (
    ComponentType,
    PlacedComponent,
    SceneComponent,
    SceneLayout,
    SceneMetadata,
    SceneResult,
    SceneSpec,
    SceneType,
)
from scene_generation.scene_renderer import (
    SceneExportFormat,
    SceneRenderer,
    SceneRenderingBackend,
)
from scene_generation.scene_templates import (
    FIXTURES,
    earth_scene,
    get_fixture,
    human_heart_scene,
    motherboard_scene,
    photosynthesis_scene,
    solar_system_scene,
)
from scene_generation.timeline import TimelineBuilder, TimelineElement
from scene_generation.transition import Transition, TransitionType

__all__ = [
    "CameraEvent",
    "CameraPlanner",
    "CameraState",
    "ComponentType",
    "FIXTURES",
    "PlacedComponent",
    "SceneBuilder",
    "SceneComponent",
    "SceneEngine",
    "SceneExportFormat",
    "SceneLayout",
    "SceneLayoutEngine",
    "SceneMetadata",
    "SceneRenderer",
    "SceneRenderingBackend",
    "SceneResult",
    "SceneSpec",
    "SceneType",
    "TimelineBuilder",
    "TimelineElement",
    "Transition",
    "TransitionType",
    "earth_scene",
    "get_fixture",
    "human_heart_scene",
    "motherboard_scene",
    "photosynthesis_scene",
    "solar_system_scene",
]
