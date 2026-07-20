"""Playback controller — render modes for timeline playback."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from video_renderer.frame_scheduler import FrameScheduler, ScheduledFrame
from video_renderer.fps_manager import FpsManager


class PlaybackMode(str, Enum):
    ENTIRE = "entire"
    TIME_RANGE = "time_range"
    FRAME_RANGE = "frame_range"
    PREVIEW = "preview"


@dataclass(slots=True)
class PlaybackRequest:
    """Parameters controlling which frames to render."""

    mode: PlaybackMode = PlaybackMode.ENTIRE
    fps: int | None = None
    preview_mode: float = 1.0
    time_start: float | None = None
    time_end: float | None = None
    frame_start: int = 0
    frame_end: int | None = None
    output_dir: str | None = None


class PlaybackController:
    """Plan frame schedules for different playback modes."""

    def __init__(
        self,
        *,
        fps_manager: FpsManager | None = None,
        scheduler: FrameScheduler | None = None,
    ) -> None:
        self._fps = fps_manager or FpsManager()
        self._scheduler = scheduler or FrameScheduler(fps_manager=self._fps)

    def resolve_duration(self, scene: dict[str, Any], timeline: dict[str, Any]) -> float:
        for key in ("duration",):
            if timeline.get(key):
                return float(timeline[key])
            if scene.get(key):
                return float(scene[key])
        return 5.0

    def resolve_fps(self, request: PlaybackRequest, timeline: dict[str, Any]) -> int:
        return self._fps.resolve(request.fps, timeline=timeline)

    def plan(
        self,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        request: PlaybackRequest,
    ) -> tuple[list[ScheduledFrame], int, float, int]:
        duration = self.resolve_duration(scene, timeline)
        fps = self.resolve_fps(request, timeline)
        total_frames = self._fps.frame_count(duration, fps)

        preview = request.preview_mode
        time_start = request.time_start
        time_end = request.time_end
        frame_start = request.frame_start
        frame_end = request.frame_end

        if request.mode == PlaybackMode.ENTIRE:
            pass
        elif request.mode == PlaybackMode.TIME_RANGE:
            time_start = request.time_start if request.time_start is not None else 0.0
            time_end = request.time_end if request.time_end is not None else duration
        elif request.mode == PlaybackMode.FRAME_RANGE:
            frame_end = request.frame_end if request.frame_end is not None else total_frames - 1
        elif request.mode == PlaybackMode.PREVIEW:
            preview = request.preview_mode if request.preview_mode < 1.0 else 0.5

        schedule = self._scheduler.schedule(
            duration=duration,
            fps=fps,
            frame_start=frame_start,
            frame_end=frame_end,
            time_start=time_start,
            time_end=time_end,
            preview_mode=preview,
        )
        return schedule, fps, duration, total_frames
