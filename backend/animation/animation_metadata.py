"""Animation metadata schemas for Phase 5.9."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AnimationType(str, Enum):
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    SCALE = "scale"
    ROTATE = "rotate"
    HIGHLIGHT = "highlight"
    PULSE = "pulse"
    DRAW_ARROW = "draw_arrow"
    WRITE_LABEL = "write_label"
    SEQUENTIAL_REVEAL = "sequential_reveal"


class CameraAnimationType(str, Enum):
    STATIC = "static"
    PAN = "pan"
    ZOOM = "zoom"
    FOCUS_REGION = "focus_region"
    FOLLOW_TARGET = "follow_target"
    KEN_BURNS = "ken_burns"


class SceneTransitionType(str, Enum):
    CROSSFADE = "crossfade"
    CUT = "cut"
    PUSH = "push"
    SLIDE = "slide"
    DISSOLVE = "dissolve"
    FADE_THROUGH_WHITE = "fade_through_white"


@dataclass(slots=True)
class AnimationClip:
    """Single animation on a scene target."""

    animation_id: str
    target: str
    animation_type: AnimationType
    start_time: float
    end_time: float
    duration: float
    easing: str = "ease-in-out"
    delay: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["animation_type"] = self.animation_type.value
        return d


@dataclass(slots=True)
class Keyframe:
    """Interpolated state at a point in time."""

    time: float
    target: str
    position: tuple[float, float] = (0.0, 0.0)
    scale: tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    opacity: float = 1.0
    camera: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CameraAnimationEvent:
    """Timed camera instruction for future renderers."""

    event_id: str
    camera_type: CameraAnimationType
    start_time: float
    end_time: float
    zoom: float = 1.0
    pan: tuple[float, float] = (0.0, 0.0)
    focus_region: tuple[float, float, float, float] | None = None
    follow_target: str | None = None
    easing: str = "ease-in-out"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["camera_type"] = self.camera_type.value
        return d


@dataclass(slots=True)
class SceneTransition:
    """Entry or exit transition for a scene."""

    transition_id: str
    transition_type: SceneTransitionType
    start_time: float
    end_time: float
    duration: float
    phase: str  # entry | exit
    easing: str = "ease-in-out"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["transition_type"] = self.transition_type.value
        return d


@dataclass(slots=True)
class AnimationTimelineMetadata:
    """Full animation timeline for one scene."""

    timeline_id: str
    scene_id: str
    animations: list[dict[str, Any]]
    camera_events: list[dict[str, Any]]
    keyframes: list[dict[str, Any]]
    transitions: list[dict[str, Any]]
    duration: float
    fps: int = 30
    scene_title: str = ""
    preset_id: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def create(
        *,
        scene_id: str,
        animations: list[AnimationClip],
        camera_events: list[CameraAnimationEvent],
        keyframes: list[Keyframe],
        transitions: list[SceneTransition],
        duration: float,
        fps: int = 30,
        scene_title: str = "",
        preset_id: str | None = None,
    ) -> AnimationTimelineMetadata:
        return AnimationTimelineMetadata(
            timeline_id=str(uuid4()),
            scene_id=scene_id,
            animations=[a.to_dict() for a in animations],
            camera_events=[c.to_dict() for c in camera_events],
            keyframes=[k.to_dict() for k in keyframes],
            transitions=[t.to_dict() for t in transitions],
            duration=duration,
            fps=fps,
            scene_title=scene_title,
            preset_id=preset_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(slots=True)
class TimelineBuildResult:
    """Output of timeline engine build + export."""

    metadata: AnimationTimelineMetadata
    timeline_path: str | None = None
    animation_path: str | None = None


# --- Future sync interfaces (audio not implemented) ---


class SyncProvider:
    """Base interface for future narration / caption / music sync."""

    def get_cues(self, scene_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class NullSyncProvider(SyncProvider):
    """Placeholder — no audio cues."""

    def get_cues(self, scene_id: str) -> list[dict[str, Any]]:
        _ = scene_id
        return []


class NarrationSyncProvider(SyncProvider):
    """Future voice narration sync — returns word/phrase timestamps."""

    def __init__(self, cues: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._cues = cues or {}

    def get_cues(self, scene_id: str) -> list[dict[str, Any]]:
        return list(self._cues.get(scene_id, []))
