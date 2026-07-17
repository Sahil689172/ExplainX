"""LayerManager — compose background + objects into one scene image."""

from __future__ import annotations

from pathlib import Path

from app.features.renderer.layers.background_layer import BackgroundLayer
from app.features.renderer.layers.object_layer import ObjectLayer
from app.features.renderer.objects.sprite import Sprite
from app.features.renderer.objects.transform import Transform
from app.features.renderer.scene_schemas import SceneDefinition, SceneObjectDefinition


class LayerManager:
    """Compose Background → Objects (z-order) into a single RGBA/RGB frame source."""

    def build_background(
        self,
        project_root: Path,
        scene: SceneDefinition,
        *,
        resolve_image,
    ) -> BackgroundLayer:
        ref = scene.background_ref()
        path = resolve_image(project_root, ref)
        return BackgroundLayer(image_path=path, label=Path(ref).name)

    def build_object_layer(
        self,
        project_root: Path,
        scene: SceneDefinition,
        *,
        resolve_image,
    ) -> ObjectLayer:
        sprites: list[Sprite] = []
        for obj in scene.objects:
            sprites.append(self._sprite_from_definition(project_root, obj, resolve_image=resolve_image))
        return ObjectLayer(sprites=sprites)

    def compose(
        self,
        background: BackgroundLayer,
        objects: ObjectLayer,
    ):
        """Return RGBA canvas: background then objects by z_index."""
        canvas = background.render()
        objects.draw(canvas)
        return canvas

    def compose_scene(
        self,
        project_root: Path,
        scene: SceneDefinition,
        *,
        resolve_image,
    ):
        """Build layers from a scene definition and compose them."""
        background = self.build_background(
            project_root, scene, resolve_image=resolve_image
        )
        objects = self.build_object_layer(
            project_root, scene, resolve_image=resolve_image
        )
        self.log_layers(background=background, objects=objects)
        return self.compose(background, objects)

    @staticmethod
    def log_layers(*, background: BackgroundLayer, objects: ObjectLayer) -> None:
        print("[Layer]", flush=True)
        print("Background:", flush=True)
        print(background.label, flush=True)
        print("Objects:", flush=True)
        print(str(len(objects.sprites)), flush=True)
        print("Draw Order:", flush=True)
        order = objects.draw_order_ids()
        if not order:
            print("(none)", flush=True)
        else:
            for obj_id in order:
                print(obj_id, flush=True)

    @staticmethod
    def _sprite_from_definition(
        project_root: Path,
        obj: SceneObjectDefinition,
        *,
        resolve_image,
    ) -> Sprite:
        path = resolve_image(project_root, obj.image)
        transform = Transform(
            x=obj.x,
            y=obj.y,
            scale=obj.scale,
            rotation=obj.rotation,
            opacity=obj.opacity,
            visible=obj.visible,
        )
        return Sprite(
            id=obj.id,
            image_path=path,
            transform=transform,
            z_index=obj.z_index,
        )
