"""Object layer — draw sprites sorted by z_index."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.features.renderer.objects.sprite import Sprite


@dataclass(slots=True)
class ObjectLayer:
    """Composite sprites onto a canvas in z-order."""

    sprites: list[Sprite] = field(default_factory=list)

    def ordered_sprites(self) -> list[Sprite]:
        """Stable draw order: ascending z_index, then id."""
        return sorted(self.sprites, key=lambda s: (s.z_index, s.id))

    def draw_order_ids(self) -> list[str]:
        return [s.id for s in self.ordered_sprites() if s.transform.visible]

    def draw(self, canvas):  # noqa: ANN001, ANN201
        """Draw sprites centered on their manifest ``x, y`` coordinates."""
        for sprite in self.ordered_sprites():
            tf = sprite.transform
            if not tf.visible or tf.opacity <= 0.0:
                continue
            raw = sprite.load_rgba()
            drawn = sprite.apply_transform(raw)
            object_width, object_height = drawn.size

            # Manifest coordinates represent the visual center after transforms.
            left = int(round(tf.x - object_width / 2))
            top = int(round(tf.y - object_height / 2))
            right = left + object_width
            bottom = top + object_height

            self._log_bounds(
                sprite_id=sprite.id,
                center=(tf.x, tf.y),
                size=(object_width, object_height),
                bounds=(left, top, right, bottom),
            )

            canvas_width, canvas_height = canvas.size
            clip_left = max(0, left)
            clip_top = max(0, top)
            clip_right = min(canvas_width, right)
            clip_bottom = min(canvas_height, bottom)

            if clip_left >= clip_right or clip_top >= clip_bottom:
                print("[Warning]", flush=True)
                print(f"Object {sprite.id} outside viewport", flush=True)
                continue

            # Crop the transformed sprite to the canvas intersection, then paste.
            source_box = (
                clip_left - left,
                clip_top - top,
                clip_right - left,
                clip_bottom - top,
            )
            clipped = drawn.crop(source_box)
            canvas.alpha_composite(clipped, dest=(clip_left, clip_top))
        return canvas

    @staticmethod
    def _log_bounds(
        *,
        sprite_id: str,
        center: tuple[float, float],
        size: tuple[int, int],
        bounds: tuple[int, int, int, int],
    ) -> None:
        """Temporary positioning diagnostics for Phase 4."""
        left, top, right, bottom = bounds
        print(f"Object: {sprite_id}", flush=True)
        print("Center:", flush=True)
        print(f"({center[0]:g},{center[1]:g})", flush=True)
        print("Scaled Size:", flush=True)
        print(f"{size[0]}x{size[1]}", flush=True)
        print("Top Left:", flush=True)
        print(f"({left},{top})", flush=True)
        print("Bottom Right:", flush=True)
        print(f"({right},{bottom})", flush=True)
