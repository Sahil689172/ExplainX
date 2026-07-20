"""Timeline player — render ordered frame sequences via FrameEngine."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from image_generation.logger import get_engine_logger
from video_renderer.frame_engine import FrameEngine
from video_renderer.frame_exporter import FrameExporter
from video_renderer.playback_controller import PlaybackController, PlaybackMode, PlaybackRequest
from video_renderer.playback_metadata import PlaybackMetadata
from video_renderer.render_session import RenderSession


class TimelinePlayer:
    """Generate an ordered sequence of rendered PNG frames from Scene + Timeline JSON.

  Architecture
  ------------
  Timeline JSON → Timeline Player → Frame Renderer → Frame Sequence

  Future: output folder feeds FFmpeg, MoviePy, Remotion, or OpenGL without API changes.
    """

    def __init__(
        self,
        *,
        frame_engine: FrameEngine | None = None,
        controller: PlaybackController | None = None,
        exporter: FrameExporter | None = None,
        logger=None,
    ) -> None:
        self._engine = frame_engine or FrameEngine()
        self._controller = controller or PlaybackController()
        self._exporter = exporter or FrameExporter()
        self._log = logger or get_engine_logger("video_renderer")

    def play_timeline(
        self,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        *,
        output_dir: str | Path = "output",
        fps: int | None = None,
        preview_mode: float = 1.0,
        mode: PlaybackMode = PlaybackMode.ENTIRE,
        time_start: float | None = None,
        time_end: float | None = None,
        frame_start: int = 0,
        frame_end: int | None = None,
    ) -> PlaybackMetadata:
        """Render every scheduled frame and export PNGs. Returns playback metadata."""
        request = PlaybackRequest(
            mode=mode,
            fps=fps,
            preview_mode=preview_mode,
            time_start=time_start,
            time_end=time_end,
            frame_start=frame_start,
            frame_end=frame_end,
        )
        schedule, resolved_fps, duration, total_frames = self._controller.plan(
            scene, timeline, request
        )

        scene_name = str(scene.get("title", scene.get("topic", "scene")))
        scene_out = self._exporter.scene_output_dir(output_dir, scene_name)

        session = RenderSession.start(
            scene=scene,
            fps=resolved_fps,
            duration=duration,
            output_directory=str(scene_out),
            preview_mode=preview_mode,
        )

        self._log.info(
            "PLAYBACK_STARTED session_id=%s scene_id=%s fps=%s frames=%s preview=%.0f%%",
            session.session_id,
            session.scene_id,
            resolved_fps,
            len(schedule),
            preview_mode * 100,
        )

        t0 = time.perf_counter()
        for scheduled in schedule:
            image = self._engine.render_frame(scene, timeline, scheduled.timestamp)
            self._log.info(
                "FRAME_RENDERED index=%s time=%.3f export_index=%s",
                scheduled.frame_index,
                scheduled.timestamp,
                scheduled.export_index,
            )
            path = self._exporter.export(image, scene_out, scheduled.export_index)
            session.record_frame(timestamp=scheduled.timestamp, path=path)

        render_time = time.perf_counter() - t0
        self._log.info(
            "PLAYBACK_COMPLETED session_id=%s exported=%s render_time=%.2fs",
            session.session_id,
            session.frames_exported,
            render_time,
        )

        frame_range = None
        if schedule:
            frame_range = (schedule[0].frame_index, schedule[-1].frame_index)

        time_range = None
        if time_start is not None or time_end is not None:
            time_range = (
                time_start if time_start is not None else 0.0,
                time_end if time_end is not None else duration,
            )

        return PlaybackMetadata.create(
            session_id=session.session_id,
            scene_id=session.scene_id,
            scene_name=session.scene_name,
            fps=resolved_fps,
            duration=duration,
            frame_count=total_frames,
            exported_count=session.frames_exported,
            output_directory=str(scene_out),
            render_time_seconds=render_time,
            start_time=session.started_at,
            preview_mode=preview_mode,
            frame_range=frame_range,
            time_range=time_range,
            timestamps=session.timestamps,
            frame_files=session.frame_files,
        )

    def play_preview(
        self,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        *,
        output_dir: str | Path = "output",
        preview_mode: float = 0.5,
        fps: int | None = None,
    ) -> PlaybackMetadata:
        """Rapid iteration — skip frames (25% / 50% / 100%)."""
        return self.play_timeline(
            scene,
            timeline,
            output_dir=output_dir,
            fps=fps,
            preview_mode=preview_mode,
            mode=PlaybackMode.PREVIEW,
        )
