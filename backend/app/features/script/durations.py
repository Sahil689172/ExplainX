"""ExplainX V1 educational script duration and pacing constants (Phase 3.6).

V1 supports ONE format: a 2–3 minute animated explainer narration.
Multiple duration presets from Phase 3 are retired.
"""

from __future__ import annotations

# Canonical V1 target (midpoint of 120–180s).
V1_TARGET_DURATION_SEC = 150

# Hard acceptance window for generated scripts.
V1_MIN_DURATION_SEC = 120
V1_MAX_DURATION_SEC = 180

# Word targets at ~140 WPM for 2–3 minutes.
V1_TARGET_WORDS_MIN = 320
V1_TARGET_WORDS_MAX = 420
V1_MIN_WORDS = 300
V1_MAX_WORDS = 450

# Spoken pacing band (words per minute).
V1_WPM_MIN = 135.0
V1_WPM_MAX = 145.0
V1_WPM = 140.0

# Downstream scene planning hints (not Scene Planning itself).
V1_SCENE_COUNT_MIN = 18
V1_SCENE_COUNT_MAX = 25
V1_SCENE_DURATION_MIN_SEC = 6.0
V1_SCENE_DURATION_MAX_SEC = 10.0

# Backward-compatible aliases used by older call sites.
WORDS_PER_MINUTE = V1_WPM
DEFAULT_TARGET_DURATION_SEC = V1_TARGET_DURATION_SEC


def word_budget(target_duration_sec: int | None = None) -> int:
    """Word budget for V1 (ignores multi-duration presets)."""
    duration = target_duration_sec or V1_TARGET_DURATION_SEC
    duration = max(V1_MIN_DURATION_SEC, min(V1_MAX_DURATION_SEC, duration))
    return int(round((V1_WPM / 60.0) * duration))


def resolve_target_duration_sec(
    *,
    label: str | None = None,
    seconds: int | None = None,
) -> int:
    """V1 always returns the canonical 150s target.

    Optional request fields are accepted for API compatibility but ignored.
    """
    _ = label, seconds
    return V1_TARGET_DURATION_SEC


def label_for_seconds(seconds: int) -> str:
    if seconds == V1_TARGET_DURATION_SEC:
        return "2-3min"
    return f"{seconds}s"


def estimate_scene_count(estimated_duration_sec: float) -> int:
    """Estimate scene count for a 2–3 minute explainer (6–10s scenes)."""
    if estimated_duration_sec <= 0:
        return V1_SCENE_COUNT_MIN
    # Prefer ~7.5s average scene length.
    raw = int(round(estimated_duration_sec / 7.5))
    return max(V1_SCENE_COUNT_MIN, min(V1_SCENE_COUNT_MAX, raw))


def duration_from_words(word_count: int, *, wpm: float = V1_WPM) -> float:
    return round((word_count / wpm) * 60.0, 1)
