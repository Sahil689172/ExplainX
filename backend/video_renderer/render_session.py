"""Render session state for one playback run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class RenderSession:
    """Mutable session tracking during playback."""

    session_id: str
    scene_id: str
    scene_name: str
    fps: int
    duration: float
    output_directory: str
    preview_mode: float = 1.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    frames_rendered: int = 0
    frames_exported: int = 0
    frame_files: list[str] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)

    @staticmethod
    def start(
        *,
        scene: dict[str, Any],
        fps: int,
        duration: float,
        output_directory: str,
        preview_mode: float = 1.0,
    ) -> RenderSession:
        title = str(scene.get("title", scene.get("topic", "scene")))
        return RenderSession(
            session_id=str(uuid4()),
            scene_id=str(scene.get("scene_id", "")),
            scene_name=title,
            fps=fps,
            duration=duration,
            output_directory=output_directory,
            preview_mode=preview_mode,
        )

    def record_frame(self, *, timestamp: float, path: str) -> None:
        self.frames_rendered += 1
        self.frames_exported += 1
        self.timestamps.append(timestamp)
        self.frame_files.append(path)

    def elapsed_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()
