"""Scene entry/exit transition generation."""

from __future__ import annotations

from uuid import uuid4

from animation.animation_metadata import SceneTransition, SceneTransitionType
from animation.animation_library import AnimationPreset
from image_generation.logger import get_engine_logger


class TransitionEngine:
    """Generate entry and exit transitions for a scene."""

    DEFAULT_ENTRY_DURATION = 0.5
    DEFAULT_EXIT_DURATION = 0.4

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("animation")

    def build(
        self,
        *,
        duration: float,
        preset: AnimationPreset,
    ) -> list[SceneTransition]:
        entry_dur = self._duration_for(preset.entry_transition, self.DEFAULT_ENTRY_DURATION)
        exit_dur = self._duration_for(preset.exit_transition, self.DEFAULT_EXIT_DURATION)
        exit_start = max(0.0, duration - exit_dur)

        transitions = [
            SceneTransition(
                transition_id=str(uuid4()),
                transition_type=preset.entry_transition,
                start_time=0.0,
                end_time=entry_dur,
                duration=entry_dur,
                phase="entry",
            ),
            SceneTransition(
                transition_id=str(uuid4()),
                transition_type=preset.exit_transition,
                start_time=exit_start,
                end_time=duration,
                duration=exit_dur,
                phase="exit",
            ),
        ]
        for tr in transitions:
            self._log.info(
                "TRANSITION_CREATED phase=%s type=%s start=%.2f end=%.2f",
                tr.phase,
                tr.transition_type.value,
                tr.start_time,
                tr.end_time,
            )
        return transitions

    def _duration_for(self, t_type: SceneTransitionType, default: float) -> float:
        if t_type == SceneTransitionType.CUT:
            return 0.0
        if t_type in (SceneTransitionType.DISSOLVE, SceneTransitionType.FADE_THROUGH_WHITE):
            return default * 1.2
        return default
