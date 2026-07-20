"""Phase 5.9 — Animation Timeline Engine."""

from animation.animation_builder import AnimationBuilder
from animation.animation_library import PRESETS, get_preset, list_presets
from animation.animation_metadata import (
    AnimationClip,
    AnimationTimelineMetadata,
    AnimationType,
    CameraAnimationEvent,
    CameraAnimationType,
    Keyframe,
    NarrationSyncProvider,
    NullSyncProvider,
    SceneTransition,
    SceneTransitionType,
    SyncProvider,
    TimelineBuildResult,
)
from animation.camera_animation import CameraAnimationEngine
from animation.easing import Easing, EasingName
from animation.keyframes import KeyframeGenerator
from animation.timeline_engine import TimelineEngine
from animation.timeline_serializer import TimelineSerializer
from animation.transition_engine import TransitionEngine

__all__ = [
    "AnimationBuilder",
    "AnimationClip",
    "AnimationTimelineMetadata",
    "AnimationType",
    "CameraAnimationEngine",
    "CameraAnimationEvent",
    "CameraAnimationType",
    "Easing",
    "EasingName",
    "Keyframe",
    "KeyframeGenerator",
    "NarrationSyncProvider",
    "NullSyncProvider",
    "PRESETS",
    "SceneTransition",
    "SceneTransitionType",
    "SyncProvider",
    "TimelineBuildResult",
    "TimelineEngine",
    "TimelineSerializer",
    "TransitionEngine",
    "get_preset",
    "list_presets",
]
