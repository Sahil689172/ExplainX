"""FPS management for timeline playback."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_FPS: tuple[int, ...] = (24, 30, 60)
FUTURE_FPS: tuple[int, ...] = (120,)


@dataclass(frozen=True, slots=True)
class FpsProfile:
    fps: int
    frame_duration: float


class FpsManager:
    """Resolve FPS, frame duration, and total frame count."""

    DEFAULT_FPS = 30

    def resolve(self, fps: int | None, *, timeline: dict | None = None) -> int:
        if timeline and timeline.get("fps"):
            fps = int(timeline["fps"])
        if fps is None:
            fps = self.DEFAULT_FPS
        if fps not in SUPPORTED_FPS and fps not in FUTURE_FPS:
            # Snap to nearest supported
            fps = min(SUPPORTED_FPS, key=lambda f: abs(f - fps))
        return fps

    def profile(self, fps: int) -> FpsProfile:
        fps = self.resolve(fps)
        return FpsProfile(fps=fps, frame_duration=1.0 / fps)

    def frame_count(self, duration: float, fps: int) -> int:
        """Total frames covering ``[0, duration)`` at the given FPS."""
        if duration <= 0:
            return 1
        fps = self.resolve(fps)
        return max(1, int(round(duration * fps)))

    def timestamp_for_frame(self, frame_index: int, fps: int) -> float:
        fps = self.resolve(fps)
        return round(frame_index / fps, 6)

    def frame_index_for_time(self, time_s: float, fps: int) -> int:
        fps = self.resolve(fps)
        return max(0, int(round(time_s * fps)))
