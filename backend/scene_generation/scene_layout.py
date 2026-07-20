"""Scene layout engine — place assets, diagrams, and text without overlap."""

from __future__ import annotations

from typing import Sequence

from image_generation.diagram_composer.geometry import Point, Rect
from image_generation.logger import get_engine_logger
from scene_generation.scene_metadata import (
    ComponentType,
    PlacedComponent,
    SceneComponent,
    SceneLayout,
    SceneSpec,
)


class SceneLayoutEngine:
    """Automatically place scene components on a slide canvas."""

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("scene_generation")

    def layout(
        self,
        components: Sequence[SceneComponent],
        spec: SceneSpec,
    ) -> list[PlacedComponent]:
        self._log.info(
            "LAYOUT_SELECTED layout=%s scene_type=%s components=%s",
            spec.layout.value,
            spec.scene_type.value,
            len(components),
        )
        w, h = float(spec.width), float(spec.height)
        margin = 48.0
        header_h = 100.0
        footer_h = 40.0
        content = Rect(margin, margin + header_h, w - 2 * margin, h - header_h - footer_h - margin)
        occupied: list[Rect] = []
        placed: list[PlacedComponent] = []

        # Header stack
        for comp in components:
            if comp.component_type == ComponentType.BACKGROUND:
                placed.append(
                    PlacedComponent(
                        component=comp,
                        bounds=Rect(0, 0, w, h),
                        position=Point(0, 0),
                    )
                )
                continue
            if comp.component_type == ComponentType.TITLE:
                bounds = Rect(margin, margin, w - 2 * margin, 44)
                placed.append(self._place(comp, bounds, occupied))
                continue
            if comp.component_type == ComponentType.SUBTITLE:
                bounds = Rect(margin, margin + 48, w - 2 * margin, 28)
                placed.append(self._place(comp, bounds, occupied))
                continue

        # Main content by layout
        main_components = [
            c
            for c in components
            if c.component_type
            not in (
                ComponentType.BACKGROUND,
                ComponentType.TITLE,
                ComponentType.SUBTITLE,
                ComponentType.FOOTER,
                ComponentType.CAPTION,
                ComponentType.LEGEND,
            )
        ]
        slots = self._content_slots(spec.layout, content)
        slot_idx = 0
        for comp in main_components:
            if slot_idx >= len(slots):
                slot_idx = len(slots) - 1
            slot = slots[slot_idx]
            bounds = self._fit_slot(comp, slot, occupied)
            placed.append(self._place(comp, bounds, occupied))
            if comp.component_type in (ComponentType.ASSET, ComponentType.DIAGRAM):
                if comp.component_type == ComponentType.ASSET:
                    self._log.info(
                        "ASSET_PLACED id=%s x=%.1f y=%.1f",
                        comp.component_id,
                        bounds.x,
                        bounds.y,
                    )
                else:
                    self._log.info(
                        "DIAGRAM_PLACED id=%s x=%.1f y=%.1f",
                        comp.component_id,
                        bounds.x,
                        bounds.y,
                    )
            slot_idx += 1

        for comp in components:
            if comp.component_type == ComponentType.LEGEND:
                bounds = Rect(content.right - 230, content.y + 8, 220, 110)
                placed.append(self._place(comp, bounds, occupied))

        # Footer / caption
        for comp in components:
            if comp.component_type == ComponentType.CAPTION:
                bounds = Rect(margin, h - margin - footer_h - 24, w - 2 * margin, 24)
                placed.append(self._place(comp, bounds, occupied))
            elif comp.component_type == ComponentType.FOOTER:
                bounds = Rect(margin, h - margin - 20, w - 2 * margin, 20)
                placed.append(self._place(comp, bounds, occupied))

        return placed

    def _content_slots(self, layout: SceneLayout, content: Rect) -> list[Rect]:
        if layout == SceneLayout.CENTERED:
            return [Rect(content.center.x - content.width * 0.3, content.y, content.width * 0.6, content.height)]
        if layout == SceneLayout.HERO:
            return [Rect(content.x, content.y, content.width, content.height * 0.72)]
        if layout == SceneLayout.LEFT_ILLUSTRATION:
            return [
                Rect(content.x, content.y, content.width * 0.52, content.height),
                Rect(content.x + content.width * 0.56, content.y, content.width * 0.42, content.height),
            ]
        if layout == SceneLayout.RIGHT_ILLUSTRATION:
            return [
                Rect(content.x + content.width * 0.48, content.y, content.width * 0.52, content.height),
                Rect(content.x, content.y, content.width * 0.42, content.height),
            ]
        if layout == SceneLayout.TWO_COLUMN:
            half = content.width / 2 - 8
            return [
                Rect(content.x, content.y, half, content.height),
                Rect(content.x + half + 16, content.y, half, content.height),
            ]
        if layout == SceneLayout.THREE_COLUMN:
            col = content.width / 3 - 10
            return [
                Rect(content.x, content.y, col, content.height),
                Rect(content.x + col + 12, content.y, col, content.height),
                Rect(content.x + 2 * (col + 12), content.y, col, content.height),
            ]
        if layout == SceneLayout.COMPARISON:
            half = content.width / 2 - 12
            return [
                Rect(content.x, content.y, half, content.height * 0.7),
                Rect(content.x + half + 24, content.y, half, content.height * 0.7),
                Rect(content.x, content.y + content.height * 0.72, content.width, content.height * 0.25),
            ]
        if layout == SceneLayout.GRID:
            cw, ch = content.width / 2 - 8, content.height / 2 - 8
            return [
                Rect(content.x, content.y, cw, ch),
                Rect(content.x + cw + 16, content.y, cw, ch),
                Rect(content.x, content.y + ch + 16, cw, ch),
                Rect(content.x + cw + 16, content.y + ch + 16, cw, ch),
            ]
        # default centered
        return [Rect(content.x, content.y, content.width, content.height)]

    def _fit_slot(
        self, comp: SceneComponent, slot: Rect, occupied: Sequence[Rect]
    ) -> Rect:
        if comp.component_type == ComponentType.BULLET_LIST:
            return slot
        if comp.component_type in (ComponentType.ASSET, ComponentType.DIAGRAM):
            # Square-ish fit inside slot
            side = min(slot.width, slot.height)
            return Rect(
                slot.x + (slot.width - side) / 2,
                slot.y + (slot.height - side) / 2,
                side,
                side,
            )
        if comp.component_type == ComponentType.LEGEND:
            return Rect(slot.right - 220, slot.bottom - 120, 210, 110)
        return slot

    def _place(
        self, comp: SceneComponent, bounds: Rect, occupied: list[Rect]
    ) -> PlacedComponent:
        trial = bounds
        for other in occupied:
            if trial.intersects(other):
                trial = Rect(trial.x, trial.y + other.height + 8, trial.width, trial.height)
        occupied.append(trial.inflate(4))
        return PlacedComponent(
            component=comp,
            bounds=trial,
            position=Point(trial.x, trial.y),
        )
