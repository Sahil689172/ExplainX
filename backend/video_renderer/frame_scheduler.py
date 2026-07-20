"""Frame scheduling — timestamps and frame indices for playback."""

from __future__ import annotations

from dataclasses import dataclass

from video_renderer.fps_manager import FpsManager


@dataclass(slots=True)
class ScheduledFrame:
    """One frame to render in the playback sequence."""

    frame_index: int
    timestamp: float
    export_index: int


class FrameScheduler:
    """Generate ordered frame indices and timestamps."""

    def __init__(self, *, fps_manager: FpsManager | None = None) -> None:
        self._fps = fps_manager or FpsManager()

    def schedule(
        self,
        *,
        duration: float,
        fps: int,
        frame_start: int = 0,
        frame_end: int | None = None,
        time_start: float | None = None,
        time_end: float | None = None,
        preview_mode: float = 1.0,
    ) -> list[ScheduledFrame]:
        fps = self._fps.resolve(fps)
        total = self._fps.frame_count(duration, fps)

        start = frame_start
        end = frame_end if frame_end is not None else total - 1
        end = min(end, total - 1)

        if time_start is not None:
            start = max(start, self._fps.frame_index_for_time(time_start, fps))
        if time_end is not None:
            end = min(end, self._fps.frame_index_for_time(time_end, fps))

        step = self._preview_step(preview_mode)
        frames: list[ScheduledFrame] = []
        export_idx = 0
        for i in range(start, end + 1, step):
            ts = self._fps.timestamp_for_frame(i, fps)
            if time_end is not None and ts > time_end:
                break
            if time_start is not None and ts < time_start:
                continue
            frames.append(
                ScheduledFrame(
                    frame_index=i,
                    timestamp=min(ts, duration),
                    export_index=export_idx,
                )
            )
            export_idx += 1
        return frames

    def timestamps(
        self,
        *,
        duration: float,
        fps: int,
        preview_mode: float = 1.0,
    ) -> list[float]:
        return [f.timestamp for f in self.schedule(duration=duration, fps=fps, preview_mode=preview_mode)]

    @staticmethod
    def _preview_step(preview_mode: float) -> int:
        if preview_mode >= 1.0:
            return 1
        if preview_mode >= 0.5:
            return 2
        if preview_mode >= 0.25:
            return 4
        return max(1, int(round(1.0 / max(preview_mode, 0.01))))
