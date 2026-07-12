"""Supported EducationalScript target durations (Phase 3)."""

from __future__ import annotations

from typing import Literal

from app.core.errors import ValidationAppError

TargetDurationLabel = Literal["30s", "60s", "90s", "3min", "5min"]

TARGET_DURATION_SECONDS: dict[str, int] = {
    "30s": 30,
    "60s": 60,
    "90s": 90,
    "3min": 180,
    "5min": 300,
}

ALLOWED_TARGET_DURATION_SEC: frozenset[int] = frozenset(TARGET_DURATION_SECONDS.values())
DEFAULT_TARGET_DURATION_LABEL: TargetDurationLabel = "60s"
DEFAULT_TARGET_DURATION_SEC = TARGET_DURATION_SECONDS[DEFAULT_TARGET_DURATION_LABEL]

# Approximate spoken pacing for placeholder generation.
WORDS_PER_MINUTE = 150.0


def resolve_target_duration_sec(
    *,
    label: str | None = None,
    seconds: int | None = None,
) -> int:
    """Resolve a supported duration from label and/or explicit seconds."""
    if label is not None and seconds is not None:
        mapped = TARGET_DURATION_SECONDS.get(label)
        if mapped is None:
            raise ValidationAppError(
                "Unsupported target_duration label.",
                code="VALIDATION_ERROR",
                details={
                    "field": "target_duration",
                    "allowed": sorted(TARGET_DURATION_SECONDS.keys()),
                },
            )
        if seconds != mapped:
            raise ValidationAppError(
                "target_duration and target_duration_sec disagree.",
                code="VALIDATION_ERROR",
                details={"target_duration": label, "target_duration_sec": seconds},
            )
        return seconds

    if label is not None:
        mapped = TARGET_DURATION_SECONDS.get(label)
        if mapped is None:
            raise ValidationAppError(
                "Unsupported target_duration label.",
                code="VALIDATION_ERROR",
                details={
                    "field": "target_duration",
                    "allowed": sorted(TARGET_DURATION_SECONDS.keys()),
                },
            )
        return mapped

    if seconds is not None:
        if seconds not in ALLOWED_TARGET_DURATION_SEC:
            raise ValidationAppError(
                "Unsupported target_duration_sec.",
                code="VALIDATION_ERROR",
                details={
                    "field": "target_duration_sec",
                    "allowed": sorted(ALLOWED_TARGET_DURATION_SEC),
                },
            )
        return seconds

    return DEFAULT_TARGET_DURATION_SEC


def label_for_seconds(seconds: int) -> str:
    for label, value in TARGET_DURATION_SECONDS.items():
        if value == seconds:
            return label
    return f"{seconds}s"


def word_budget(target_duration_sec: int) -> int:
    """Approximate word count that fits the target spoken duration."""
    return max(20, int(round((WORDS_PER_MINUTE / 60.0) * target_duration_sec)))
