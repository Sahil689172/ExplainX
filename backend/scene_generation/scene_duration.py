"""Dynamic scene duration estimation (Task 5).

Replaces the fixed ~6 second duration with a value derived from how much
educational content a scene carries: bullets, visuals, and concept complexity.
Per-scene durations are intentionally short; a multi-scene video sums them to
reach the 20s / 45s / 90-180s ranges for simple / medium / complex topics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DurationModel:
    base_seconds: float = 4.5
    per_bullet: float = 1.8
    per_extra_asset: float = 1.4
    per_diagram: float = 1.2
    title_read: float = 1.5
    minimum: float = 6.0
    maximum: float = 16.0


def estimate_scene_duration(
    *,
    bullet_count: int = 0,
    asset_count: int = 1,
    diagram_count: int = 0,
    model: DurationModel | None = None,
) -> float:
    """Estimate a single scene's duration in seconds."""
    m = model or DurationModel()
    seconds = (
        m.base_seconds
        + m.title_read
        + m.per_bullet * max(0, bullet_count)
        + m.per_extra_asset * max(0, asset_count - 1)
        + m.per_diagram * max(0, diagram_count)
    )
    return round(max(m.minimum, min(seconds, m.maximum)), 2)


def classify_complexity(total_seconds: float) -> str:
    """Label an overall video duration."""
    if total_seconds <= 25:
        return "simple"
    if total_seconds <= 60:
        return "medium"
    return "complex"
