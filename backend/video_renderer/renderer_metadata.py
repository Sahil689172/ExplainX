"""Frame render result metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class FrameRenderMetadata:
    """Diagnostics for a single rendered frame."""

    scene_id: str
    timeline_id: str
    frame_index: int
    current_time: float
    visible_layers: int
    camera_zoom: float
    camera_pan: tuple[float, float]
    layer_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
