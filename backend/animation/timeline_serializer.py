"""Serialize animation timelines to JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from animation.animation_metadata import AnimationTimelineMetadata
from image_generation.logger import get_engine_logger


@dataclass(slots=True)
class SerializeResult:
    timeline_path: str
    animation_path: str


class TimelineSerializer:
    """Export ``timeline.json`` and ``animation.json`` for future renderers."""

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("animation")

    def export(
        self,
        metadata: AnimationTimelineMetadata,
        output_dir: str | Path,
        *,
        stem: str | None = None,
    ) -> SerializeResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = stem or metadata.timeline_id

        timeline_doc = self._timeline_document(metadata)
        animation_doc = self._animation_document(metadata)

        timeline_path = out / f"{stem}_timeline.json"
        animation_path = out / f"{stem}_animation.json"

        timeline_path.write_text(json.dumps(timeline_doc, indent=2), encoding="utf-8")
        animation_path.write_text(json.dumps(animation_doc, indent=2), encoding="utf-8")

        self._log.info(
            "TIMELINE_EXPORTED timeline_id=%s timeline=%s animation=%s",
            metadata.timeline_id,
            timeline_path,
            animation_path,
        )
        return SerializeResult(
            timeline_path=str(timeline_path),
            animation_path=str(animation_path),
        )

    def _timeline_document(self, meta: AnimationTimelineMetadata) -> dict[str, Any]:
        return {
            "timeline_id": meta.timeline_id,
            "scene_id": meta.scene_id,
            "scene_title": meta.scene_title,
            "duration": meta.duration,
            "fps": meta.fps,
            "preset_id": meta.preset_id,
            "created_at": meta.created_at,
            "transitions": meta.transitions,
            "camera_events": meta.camera_events,
            "appearance_order": [
                a["target"] for a in meta.animations if a.get("metadata", {}).get("phase") != "exit"
            ],
            "elements": meta.animations,
        }

    def _animation_document(self, meta: AnimationTimelineMetadata) -> dict[str, Any]:
        return {
            "timeline_id": meta.timeline_id,
            "scene_id": meta.scene_id,
            "duration": meta.duration,
            "fps": meta.fps,
            "animations": meta.animations,
            "keyframes": meta.keyframes,
            "camera_events": meta.camera_events,
            "transitions": meta.transitions,
            "renderer_hints": {
                "compatible": ["moviepy", "remotion", "manim", "ffmpeg", "opengl"],
            },
        }
