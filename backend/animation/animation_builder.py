"""Build animation clips from scene JSON timeline elements."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from animation.animation_library import AnimationPreset, get_preset
from animation.animation_metadata import AnimationClip, AnimationType
from image_generation.logger import get_engine_logger


class AnimationBuilder:
    """Convert scene timeline elements into animation clips."""

    DEFAULT_CLIP_DURATION = 0.6
    EXIT_LEAD = 0.5

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("animation")

    def build(
        self,
        scene_json: dict[str, Any],
        *,
        preset_id: str | None = None,
    ) -> tuple[list[AnimationClip], AnimationPreset, dict[str, dict[str, float]]]:
        preset = get_preset(preset_id, topic=scene_json.get("title"))
        timeline = scene_json.get("timeline") or {}
        elements = timeline.get("elements") or []
        scene_duration = float(scene_json.get("duration") or timeline.get("duration") or 5.0)
        bounds = self._extract_bounds(scene_json)

        animations: list[AnimationClip] = []
        for el in elements:
            target = el.get("component_id", "unknown")
            comp_type = el.get("component_type", "asset")
            start = float(el.get("start_time", 0.0))
            delay = max(0.0, start * 0.1)
            anim_type = self._resolve_animation(preset, comp_type, target)
            duration = self._clip_duration(anim_type, scene_duration, start)
            end = min(scene_duration - self.EXIT_LEAD, start + delay + duration)

            clip = AnimationClip(
                animation_id=str(uuid4()),
                target=target,
                animation_type=anim_type,
                start_time=round(start + delay, 3),
                end_time=round(end, 3),
                duration=round(max(0.1, end - start - delay), 3),
                easing="ease-in-out",
                delay=round(delay, 3),
                metadata={"component_type": comp_type},
            )
            animations.append(clip)
            self._log.info(
                "ANIMATION_CREATED target=%s type=%s start=%.2f end=%.2f",
                target,
                anim_type.value,
                clip.start_time,
                clip.end_time,
            )

            # Educational highlight beat (Task 4/7): draw attention to the main
            # diagram partway through the scene without disrupting other clips.
            if comp_type == "diagram" and scene_duration > 4.0:
                hl_start = round(scene_duration * 0.55, 3)
                hl_end = round(min(scene_duration - self.EXIT_LEAD, hl_start + 0.8), 3)
                if hl_end > hl_start:
                    animations.append(
                        AnimationClip(
                            animation_id=str(uuid4()),
                            target=target,
                            animation_type=AnimationType.HIGHLIGHT,
                            start_time=hl_start,
                            end_time=hl_end,
                            duration=round(hl_end - hl_start, 3),
                            easing="ease-in-out",
                            delay=0.0,
                            metadata={"phase": "highlight"},
                        )
                    )

            # Exit fade for visible elements
            if preset.exit_fade and comp_type not in ("background",):
                exit_start = max(clip.end_time, scene_duration - self.EXIT_LEAD)
                animations.append(
                    AnimationClip(
                        animation_id=str(uuid4()),
                        target=target,
                        animation_type=AnimationType.FADE_OUT,
                        start_time=round(exit_start, 3),
                        end_time=round(scene_duration, 3),
                        duration=round(scene_duration - exit_start, 3),
                        easing="ease-out",
                        delay=0.0,
                        metadata={"phase": "exit"},
                    )
                )

        # Bullet sequential children
        for el in elements:
            if el.get("component_type") != "bullet_list":
                continue
            bullets = el.get("bullets") or []
            base_start = float(el.get("start_time", 0.5))
            for i, _bullet in enumerate(bullets):
                t_id = f"{el.get('component_id')}_bullet_{i}"
                step = 0.35
                start = base_start + i * step
                end = start + step
                animations.append(
                    AnimationClip(
                        animation_id=str(uuid4()),
                        target=t_id,
                        animation_type=preset.bullet_animation,
                        start_time=round(start, 3),
                        end_time=round(end, 3),
                        duration=round(step, 3),
                        easing="ease-out",
                        delay=0.0,
                        metadata={"parent": el.get("component_id"), "index": i},
                    )
                )

        return animations, preset, bounds

    def _resolve_animation(
        self, preset: AnimationPreset, comp_type: str, target: str
    ) -> AnimationType:
        if comp_type in preset.component_animations:
            return preset.component_animations[comp_type]
        if "diagram" in target:
            return AnimationType.ZOOM_IN
        if "title" in target:
            return AnimationType.SLIDE_DOWN
        return AnimationType.FADE_IN

    def _clip_duration(
        self, anim_type: AnimationType, scene_duration: float, start: float
    ) -> float:
        base = self.DEFAULT_CLIP_DURATION
        if anim_type in (AnimationType.ZOOM_IN, AnimationType.ZOOM_OUT):
            base = 0.9
        if anim_type == AnimationType.SEQUENTIAL_REVEAL:
            base = 0.4
        return min(base, max(0.2, scene_duration - start - self.EXIT_LEAD))

    def _extract_bounds(self, scene_json: dict[str, Any]) -> dict[str, dict[str, float]]:
        bounds: dict[str, dict[str, float]] = {}
        for asset in scene_json.get("assets") or []:
            cid = asset.get("component_id")
            b = asset.get("bounds") or {}
            if cid:
                bounds[cid] = {
                    "x": float(b.get("x", 0)),
                    "y": float(b.get("y", 0)),
                    "width": float(b.get("width", 100)),
                    "height": float(b.get("height", 100)),
                }
        # Timeline elements may not include bullets bounds — synthesize from layout
        for el in (scene_json.get("timeline") or {}).get("elements") or []:
            cid = el.get("component_id")
            if cid and cid not in bounds:
                bounds[cid] = {"x": 80.0, "y": 200.0, "width": 400.0, "height": 300.0}
        return bounds
