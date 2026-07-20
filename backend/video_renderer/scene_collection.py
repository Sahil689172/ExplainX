"""Scene stitching — merge every scene's frames into ONE continuous sequence.

This is the architectural core of "one final video" (Task 1/2). Instead of
encoding a separate video per scene, each scene contributes PNG frames to a
single, globally-numbered frame timeline. FFmpeg is then invoked exactly once
over the merged sequence to produce ``final_video.mp4``.

    Scene 1 -> render frames -> store
    Scene 2 -> render frames -> store
    Scene N -> render frames -> store
                     |
              merge frame timeline (frame_000000 .. frame_NNNNNN)
                     |
              encode ONCE -> final_video.mp4

The class only depends on :class:`TimelinePlayer` (rendering) and copies the
resulting frames — it never invokes FFmpeg itself, keeping rendering and
encoding decoupled.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from video_renderer.timeline_player import TimelinePlayer


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in str(name).strip()).strip("_") or "scene"


@dataclass(slots=True)
class SceneClip:
    """One renderable scene: its scene JSON, animation JSON, and fps."""

    name: str
    scene: dict[str, Any]
    animation: dict[str, Any]
    fps: int = 30


@dataclass(slots=True)
class SceneFrameStats:
    """Where a scene's frames landed inside the merged global timeline."""

    name: str
    frame_start: int  # global index of first frame (inclusive)
    frame_end: int    # global index of last frame (inclusive)
    frame_count: int
    expected_frames: int
    duration: float
    frame_match: bool


@dataclass(slots=True)
class MergedTimeline:
    """Result of stitching: one directory of continuous ``frame_NNNNNN.png``."""

    frame_directory: Path
    frame_count: int
    fps: int
    duration: float
    scenes: list[SceneFrameStats] = field(default_factory=list)


class SceneCollection:
    """Accumulates scenes and stitches their frames into one timeline.

    Usage::

        collection = SceneCollection()
        for clip in clips:
            collection.add(clip)
        merged = collection.render(merged_dir)
        # -> encode_video(merged.frame_directory, ...) exactly once
    """

    def __init__(self, player: TimelinePlayer | None = None) -> None:
        self._player = player or TimelinePlayer()
        self._clips: list[SceneClip] = []

    def add(self, clip: SceneClip) -> None:
        self._clips.append(clip)

    def __len__(self) -> int:
        return len(self._clips)

    @property
    def clips(self) -> list[SceneClip]:
        return list(self._clips)

    def render(
        self,
        merged_dir: str | Path,
        *,
        scratch_dir: str | Path | None = None,
        on_scene: Callable[[int, SceneClip, SceneFrameStats], None] | None = None,
    ) -> MergedTimeline:
        """Render every scene and copy its frames into one continuous sequence.

        Parameters
        ----------
        merged_dir:
            Directory that will hold ``frame_000000.png`` .. ``frame_NNNNNN.png``.
            It is recreated fresh on every call.
        scratch_dir:
            Where per-scene frames are rendered before merging. Defaults to a
            ``_scenes`` sibling of ``merged_dir``.
        on_scene:
            Optional callback invoked after each scene with
            ``(index, clip, stats)`` for progress reporting.
        """
        if not self._clips:
            raise ValueError("SceneCollection is empty — add at least one scene")

        merged = Path(merged_dir)
        if merged.exists():
            shutil.rmtree(merged, ignore_errors=True)
        merged.mkdir(parents=True, exist_ok=True)

        scratch = Path(scratch_dir) if scratch_dir else merged.parent / "_scenes"
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir(parents=True, exist_ok=True)

        global_index = 0
        fps = self._clips[0].fps
        stats: list[SceneFrameStats] = []

        for i, clip in enumerate(self._clips, 1):
            scene_scratch = scratch / f"{i:02d}_{_slug(clip.name)}"
            playback = self._player.play_timeline(
                clip.scene,
                clip.animation,
                output_dir=scene_scratch,
                fps=clip.fps,
            )
            fps = playback.fps or clip.fps

            start = global_index
            for src in sorted(playback.frame_files):
                dst = merged / f"frame_{global_index:06d}.png"
                shutil.copyfile(src, dst)
                global_index += 1

            count = global_index - start
            scene_duration = float(
                clip.scene.get("duration") or clip.animation.get("duration") or 0
            )
            expected = max(1, int(round(scene_duration * fps))) if scene_duration else count
            stat = SceneFrameStats(
                name=clip.name,
                frame_start=start,
                frame_end=global_index - 1,
                frame_count=count,
                expected_frames=expected,
                duration=round(count / fps, 3) if fps else 0.0,
                frame_match=abs(count - expected) <= 1,
            )
            stats.append(stat)
            if on_scene is not None:
                on_scene(i, clip, stat)

        return MergedTimeline(
            frame_directory=merged,
            frame_count=global_index,
            fps=fps,
            duration=round(global_index / fps, 3) if fps else 0.0,
            scenes=stats,
        )
