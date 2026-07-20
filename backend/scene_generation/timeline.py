"""Timeline metadata for educational scenes (future video sync)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from scene_generation.scene_metadata import ComponentType, PlacedComponent, SceneSpec
from scene_generation.transition import Transition, TransitionType


@dataclass(slots=True)
class TimelineElement:
    """When a scene component appears during playback."""

    component_id: str
    component_type: str
    appearance_order: int
    start_time: float
    duration: float
    end_time: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TimelineBuilder:
    """Build appearance order and camera event timeline for a scene."""

    def build(
        self,
        spec: SceneSpec,
        placed: Sequence[PlacedComponent],
        *,
        camera_events: Sequence[dict[str, Any]] | None = None,
        transition: Transition | None = None,
    ) -> dict[str, Any]:
        transition = transition or Transition(TransitionType.FADE, duration_seconds=0.5)
        total = spec.duration_seconds
        ordered = sorted(
            placed,
            key=lambda p: (
                _type_order(p.component.component_type),
                p.component.z_index,
            ),
        )
        elements: list[TimelineElement] = []
        step = total / max(len(ordered), 1)
        for i, comp in enumerate(ordered):
            start = round(i * step * 0.35, 3)
            dur = round(total - start, 3)
            elements.append(
                TimelineElement(
                    component_id=comp.component.component_id,
                    component_type=comp.component.component_type.value,
                    appearance_order=i + 1,
                    start_time=start,
                    duration=dur,
                    end_time=round(start + dur, 3),
                )
            )
        return {
            "duration": total,
            "elements": [e.to_dict() for e in elements],
            "appearance_order": [e.component_id for e in elements],
            "transition": transition.to_dict(),
            "camera_events": list(camera_events or []),
        }


def _type_order(ct: ComponentType) -> int:
    order = {
        ComponentType.BACKGROUND: 0,
        ComponentType.TITLE: 1,
        ComponentType.SUBTITLE: 2,
        ComponentType.ASSET: 3,
        ComponentType.DIAGRAM: 4,
        ComponentType.BULLET_LIST: 5,
        ComponentType.LEGEND: 6,
        ComponentType.CALLOUT: 7,
        ComponentType.HIGHLIGHT_BOX: 8,
        ComponentType.CAPTION: 9,
        ComponentType.FOOTER: 10,
    }
    return order.get(ct, 99)
