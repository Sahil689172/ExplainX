"""ExplainX educational script duration and pacing constants.

MVP prioritizes a stable end-to-end pipeline over strict 2–3 minute accuracy.
Hard validation uses a wide duration window; word budgets remain guidance only.
"""

from __future__ import annotations

# Canonical generation target (prompts / outline word-budget guidance).
V1_TARGET_DURATION_SEC = 150

# MVP hard acceptance window for generated scripts.
SCRIPT_MIN_DURATION_SEC = 60
SCRIPT_MAX_DURATION_SEC = 300

# Backward-compatible aliases used by validators / tests.
V1_MIN_DURATION_SEC = SCRIPT_MIN_DURATION_SEC
V1_MAX_DURATION_SEC = SCRIPT_MAX_DURATION_SEC

# Word targets at ~140 WPM — guidance for prompts/outline only (not hard validation).
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
    """Word budget for prompt guidance (ignores multi-duration presets)."""
    duration = target_duration_sec or V1_TARGET_DURATION_SEC
    duration = max(SCRIPT_MIN_DURATION_SEC, min(SCRIPT_MAX_DURATION_SEC, duration))
    return int(round((V1_WPM / 60.0) * duration))


def resolve_target_duration_sec(
    *,
    label: str | None = None,
    seconds: int | None = None,
) -> int:
    """Always returns the canonical 150s generation target.

    Optional request fields are accepted for API compatibility but ignored.
    """
    _ = label, seconds
    return V1_TARGET_DURATION_SEC


def label_for_seconds(seconds: int) -> str:
    if seconds == V1_TARGET_DURATION_SEC:
        return "2-3min"
    return f"{seconds}s"


def estimate_scene_count(estimated_duration_sec: float) -> int:
    """Estimate scene count for an explainer (6–10s scenes)."""
    if estimated_duration_sec <= 0:
        return V1_SCENE_COUNT_MIN
    # Prefer ~7.5s average scene length.
    raw = int(round(estimated_duration_sec / 7.5))
    return max(V1_SCENE_COUNT_MIN, min(V1_SCENE_COUNT_MAX, raw))


def duration_from_words(word_count: int, *, wpm: float = V1_WPM) -> float:
    return round((word_count / wpm) * 60.0, 1)
