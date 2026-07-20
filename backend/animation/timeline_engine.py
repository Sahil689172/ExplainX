"""Animation Timeline Engine — Scene JSON → full animation timeline metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from animation.animation_builder import AnimationBuilder
from animation.animation_metadata import (
    AnimationTimelineMetadata,
    NullSyncProvider,
    SyncProvider,
    TimelineBuildResult,
)
from animation.animation_library import get_preset
from animation.camera_animation import CameraAnimationEngine
from animation.keyframes import Keyframe, KeyframeGenerator
from animation.timeline_serializer import TimelineSerializer
from animation.transition_engine import TransitionEngine
from image_generation.logger import get_engine_logger


class TimelineEngine:
    """Convert Scene JSON into a complete animation timeline (metadata only).

  Pipeline: Scene JSON → AnimationBuilder → Camera + Transitions → Keyframes
            → TimelineSerializer → timeline.json + animation.json

  Future renderers (MoviePy, Remotion, Manim, FFmpeg, OpenGL) consume exports
  without changing this engine.
    """

    def __init__(
        self,
        *,
        animation_builder: AnimationBuilder | None = None,
        camera_engine: CameraAnimationEngine | None = None,
        transition_engine: TransitionEngine | None = None,
        keyframe_generator: KeyframeGenerator | None = None,
        serializer: TimelineSerializer | None = None,
        sync_provider: SyncProvider | None = None,
        fps: int = 30,
        logger=None,
    ) -> None:
        self._builder = animation_builder or AnimationBuilder()
        self._camera = camera_engine or CameraAnimationEngine()
        self._transitions = transition_engine or TransitionEngine()
        self._keyframes = keyframe_generator or KeyframeGenerator()
        self._serializer = serializer or TimelineSerializer()
        self._sync = sync_provider or NullSyncProvider()
        self._fps = fps
        self._log = logger or get_engine_logger("animation")

    def build_from_scene(
        self,
        scene_json: dict[str, Any],
        *,
        preset_id: str | None = None,
        output_dir: str | Path | None = None,
    ) -> TimelineBuildResult:
        """Build animation timeline metadata from a Phase 5.8 scene JSON document."""
        scene_id = str(scene_json.get("scene_id", "unknown"))
        title = str(scene_json.get("title", ""))
        duration = float(
            scene_json.get("duration")
            or (scene_json.get("timeline") or {}).get("duration")
            or 5.0
        )

        self._log.info(
            "TIMELINE_CREATED scene_id=%s title=%r duration=%.2f",
            scene_id,
            title,
            duration,
        )

        animations, preset, bounds = self._builder.build(scene_json, preset_id=preset_id)
        transitions = self._transitions.build(duration=duration, preset=preset)
        camera_events = self._camera.build(
            scene_json.get("camera") or {},
            duration=duration,
            preset_camera=preset.default_camera,
            follow_target=self._primary_diagram_target(scene_json),
        )

        element_keyframes = self._keyframes.generate(animations, bounds=bounds)
        camera_kfs = self._camera.keyframes_for_events(camera_events)
        all_keyframes = self._merge_camera_keyframes(element_keyframes, camera_kfs)

        # Future sync cues (narration / captions / music) — metadata only
        sync_cues = self._sync.get_cues(scene_id)

        metadata = AnimationTimelineMetadata.create(
            scene_id=scene_id,
            animations=animations,
            camera_events=camera_events,
            keyframes=all_keyframes,
            transitions=transitions,
            duration=duration,
            fps=self._fps,
            scene_title=title,
            preset_id=preset.preset_id,
        )
        if sync_cues:
            d = metadata.to_dict()
            d["sync_cues"] = sync_cues
            # Re-wrap not needed for export — serializer reads metadata fields

        timeline_path = animation_path = None
        if output_dir is not None:
            export = self._serializer.export(metadata, output_dir, stem=scene_id)
            timeline_path = export.timeline_path
            animation_path = export.animation_path

        return TimelineBuildResult(
            metadata=metadata,
            timeline_path=timeline_path,
            animation_path=animation_path,
        )

    def build_from_file(
        self,
        scene_json_path: str | Path,
        *,
        preset_id: str | None = None,
        output_dir: str | Path | None = None,
    ) -> TimelineBuildResult:
        path = Path(scene_json_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        out = output_dir or path.parent
        return self.build_from_scene(data, preset_id=preset_id, output_dir=out)

    def _primary_diagram_target(self, scene_json: dict[str, Any]) -> str | None:
        for asset in scene_json.get("assets") or []:
            if asset.get("type") == "diagram":
                return asset.get("component_id")
        for el in (scene_json.get("timeline") or {}).get("elements") or []:
            if el.get("component_type") == "diagram":
                return el.get("component_id")
        return None

    def _merge_camera_keyframes(
        self,
        element_kfs: list[Keyframe],
        camera_kfs: list[dict[str, Any]],
    ) -> list[Keyframe]:
        merged = list(element_kfs)
        for ck in camera_kfs:
            merged.append(
                Keyframe(
                    time=ck["time"],
                    target="__camera__",
                    camera={
                        "camera_type": ck.get("camera_type"),
                        "zoom": ck.get("zoom"),
                        "pan": ck.get("pan"),
                        "focus_region": ck.get("focus_region"),
                    },
                )
            )
        merged.sort(key=lambda k: k.time)
        return merged
