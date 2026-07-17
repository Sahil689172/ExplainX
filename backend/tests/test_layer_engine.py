"""Tests for Renderer Phase 4 — Layer & Object Engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.features.projects.filesystem import ProjectFilesystem
from app.features.renderer.artifacts import RenderArtifactStore
from app.features.renderer.camera_service import CameraService
from app.features.renderer.frame_renderer import even_dimensions, render_frame
from app.features.renderer.layers.background_layer import BackgroundLayer
from app.features.renderer.layers.layer_manager import LayerManager
from app.features.renderer.layers.object_layer import ObjectLayer
from app.features.renderer.objects.sprite import Sprite
from app.features.renderer.objects.transform import Transform
from app.features.renderer.scene_manifest import (
    load_scene_manifest,
    resolve_layer_image,
    validate_manifest,
)
from app.features.renderer.scene_schemas import (
    SceneDefinition,
    SceneManifest,
    SceneObjectDefinition,
)
from app.features.renderer.scene_service import SceneComposer
from app.features.renderer.schemas import RenderConfig
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

_MINIMAL_PNG = bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

PROJECT_ID = "22222222-2222-2222-2222-222222222222"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_root=str(tmp_path),
        env="testing",
        render_fps=15,
        default_duration_seconds=60,
        frame_output_format="png",
        ffmpeg_executable="ffmpeg",
        default_zoom=1.15,
    )


def _write_solid_png(path: Path, *, size: tuple[int, int], color: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, color).save(path)


def _seed_layer_project(tmp_path: Path) -> Path:
    fs = ProjectFilesystem(_settings(tmp_path))
    root = fs.project_root(PROJECT_ID)
    assets = root / "assets"
    _write_solid_png(assets / "space.png", size=(200, 100), color=(0, 0, 40, 255))
    _write_solid_png(assets / "sun.png", size=(40, 40), color=(255, 200, 0, 255))
    _write_solid_png(assets / "earth.png", size=(40, 40), color=(0, 120, 255, 255))
    return root


def test_layer_draw_order_by_z_index(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    sprites = [
        Sprite(
            id="earth",
            image_path=root / "assets" / "earth.png",
            transform=Transform(x=10, y=10),
            z_index=2,
        ),
        Sprite(
            id="sun",
            image_path=root / "assets" / "sun.png",
            transform=Transform(x=0, y=0),
            z_index=1,
        ),
    ]
    layer = ObjectLayer(sprites=sprites)
    assert layer.draw_order_ids() == ["sun", "earth"]


def test_object_loading_and_transform(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    sprite = Sprite(
        id="sun",
        image_path=root / "assets" / "sun.png",
        transform=Transform(x=5, y=5, scale=0.5, rotation=0, opacity=1.0),
        z_index=1,
    )
    raw = sprite.load_rgba()
    assert raw.size == (40, 40)
    scaled = sprite.apply_transform(raw)
    assert scaled.size == (20, 20)


def test_object_rendering_composites_onto_background(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    bg = BackgroundLayer(image_path=root / "assets" / "space.png")
    objects = ObjectLayer(
        sprites=[
            Sprite(
                id="sun",
                image_path=root / "assets" / "sun.png",
                transform=Transform(x=10, y=10, scale=1.0),
                z_index=1,
            )
        ]
    )
    canvas = LayerManager().compose(bg, objects)
    assert canvas.size == (200, 100)
    # Pixel under sun should not remain pure background blue.
    pixel = canvas.getpixel((20, 20))
    assert pixel[0] > 100  # yellowish from sun


def test_object_coordinates_are_visual_center(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    bg = BackgroundLayer(image_path=root / "assets" / "space.png")
    objects = ObjectLayer(
        sprites=[
            Sprite(
                id="sun",
                image_path=root / "assets" / "sun.png",
                transform=Transform(x=100, y=50, scale=0.5),
                z_index=1,
            )
        ]
    )

    canvas = LayerManager().compose(bg, objects)

    # 40x40 scaled to 20x20 and centered at (100, 50).
    assert canvas.getpixel((90, 40))[0] > 100
    assert canvas.getpixel((109, 59))[0] > 100
    assert canvas.getpixel((89, 39)) == (0, 0, 40, 255)
    assert canvas.getpixel((110, 60)) == (0, 0, 40, 255)


def test_partial_object_is_clipped_safely(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    bg = BackgroundLayer(image_path=root / "assets" / "space.png")
    objects = ObjectLayer(
        sprites=[
            Sprite(
                id="sun",
                image_path=root / "assets" / "sun.png",
                transform=Transform(x=0, y=0),
                z_index=1,
            )
        ]
    )

    canvas = LayerManager().compose(bg, objects)
    assert canvas.size == (200, 100)
    assert canvas.getpixel((0, 0))[0] > 100
    assert canvas.getpixel((20, 20)) == (0, 0, 40, 255)


def test_object_completely_outside_prints_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _seed_layer_project(tmp_path)
    bg = BackgroundLayer(image_path=root / "assets" / "space.png")
    objects = ObjectLayer(
        sprites=[
            Sprite(
                id="earth",
                image_path=root / "assets" / "earth.png",
                transform=Transform(x=500, y=500),
                z_index=1,
            )
        ]
    )

    LayerManager().compose(bg, objects)
    output = capsys.readouterr().out
    assert "[Warning]" in output
    assert "Object earth outside viewport" in output


def test_z_index_higher_draws_on_top(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    bg = BackgroundLayer(image_path=root / "assets" / "space.png")
    objects = ObjectLayer(
        sprites=[
            Sprite(
                id="bottom",
                image_path=root / "assets" / "sun.png",
                transform=Transform(x=0, y=0),
                z_index=1,
            ),
            Sprite(
                id="top",
                image_path=root / "assets" / "earth.png",
                transform=Transform(x=0, y=0),
                z_index=5,
            ),
        ]
    )
    canvas = LayerManager().compose(bg, objects)
    # Top-left of both sprites — earth (blue) should win.
    pixel = canvas.getpixel((5, 5))
    assert pixel[2] > pixel[0]


def test_manifest_layered_validation(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    manifest = SceneManifest(
        fps=15,
        video_duration=6,
        scenes=[
            SceneDefinition(
                scene_id="scene_01",
                background="assets/space.png",
                duration=6,
                camera="zoom_in",
                objects=[
                    SceneObjectDefinition(
                        id="sun",
                        image="assets/sun.png",
                        x=50,
                        y=20,
                        scale=1.0,
                        z_index=1,
                    ),
                    SceneObjectDefinition(
                        id="earth",
                        image="assets/earth.png",
                        x=100,
                        y=20,
                        scale=0.5,
                        z_index=2,
                    ),
                ],
            )
        ],
    )
    validate_manifest(manifest, project_root=root)
    assert resolve_layer_image(root, "assets/sun.png").is_file()


def test_manifest_rejects_duplicate_object_ids(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    manifest = SceneManifest(
        fps=15,
        scenes=[
            SceneDefinition(
                scene_id="scene_01",
                background="assets/space.png",
                duration=6,
                objects=[
                    SceneObjectDefinition(id="sun", image="assets/sun.png", z_index=1),
                    SceneObjectDefinition(id="sun", image="assets/earth.png", z_index=2),
                ],
            )
        ],
    )
    with pytest.raises(ValidationAppError) as exc:
        validate_manifest(manifest, project_root=root)
    assert exc.value.code == "SCENE_OBJECT_DUPLICATE_ID"


def test_manifest_rejects_missing_background(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    manifest = SceneManifest(
        fps=15,
        scenes=[
            SceneDefinition(
                scene_id="scene_01",
                background="assets/missing.png",
                duration=6,
            )
        ],
    )
    with pytest.raises(ValidationAppError) as exc:
        validate_manifest(manifest, project_root=root)
    assert exc.value.code == "SCENE_BACKGROUND_NOT_FOUND"


def test_manifest_rejects_object_center_outside_render_area(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    manifest = SceneManifest(
        fps=15,
        scenes=[
            SceneDefinition(
                scene_id="scene_01",
                background="assets/space.png",
                duration=6,
                objects=[
                    SceneObjectDefinition(
                        id="earth",
                        image="assets/earth.png",
                        x=201,
                        y=50,
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValidationAppError) as exc:
        validate_manifest(manifest, project_root=root)
    assert exc.value.code == "SCENE_OBJECT_CENTER_OUTSIDE_FRAME"
    assert exc.value.details["center"] == [201.0, 50.0]
    assert exc.value.details["render_size"] == [200, 100]


def test_legacy_image_only_still_valid(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    manifest = SceneManifest(
        fps=15,
        scenes=[
            SceneDefinition(
                scene_id="scene_01",
                image="assets/space.png",
                duration=6,
                camera="center",
            )
        ],
    )
    validate_manifest(manifest, project_root=root)
    scene = manifest.scenes[0]
    assert scene.is_layered() is False
    assert scene.background_ref() == "assets/space.png"


def test_camera_compatibility_with_composed_scene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _seed_layer_project(tmp_path)
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "scene_manifest.json").write_text(
        json.dumps(
            {
                "fps": 5,
                "video_duration": 2,
                "scenes": [
                    {
                        "scene_id": "orbit",
                        "background": "assets/space.png",
                        "duration": 2,
                        "camera": "zoom_in",
                        "objects": [
                            {
                                "id": "sun",
                                "image": "assets/sun.png",
                                "x": 20,
                                "y": 20,
                                "scale": 1.0,
                                "z_index": 1,
                            },
                            {
                                "id": "earth",
                                "image": "assets/earth.png",
                                "x": 80,
                                "y": 30,
                                "scale": 0.5,
                                "z_index": 2,
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    settings = _settings(tmp_path)
    store = RenderArtifactStore(ProjectFilesystem(settings))
    config = RenderConfig(fps=5, duration_sec=2, frame_format="png")

    viewports: list[tuple[float, float]] = []

    def fake_segment(**kwargs):  # noqa: ANN003
        camera: CameraService = kwargs["camera"]
        for i in range(kwargs["fps"] * kwargs["duration_sec"]):
            vp = camera.get_viewport(i / kwargs["fps"])
            viewports.append((vp.width, vp.height))
        return kwargs["fps"] * kwargs["duration_sec"]

    monkeypatch.setattr(
        "app.features.renderer.scene_service.generate_camera_frames_segment",
        fake_segment,
    )

    composer = SceneComposer(settings=settings, store=store)
    result = composer.compose(PROJECT_ID, root, base_config=config)
    assert result.metadata.scenes[0].layered is True
    assert result.metadata.scenes[0].object_count == 2
    assert viewports[0][0] > viewports[-1][0]  # zoom_in shrinks viewport
    composed = root / "artifacts" / "composed" / "orbit_composed.png"
    assert composed.is_file()


def test_render_frame_after_layer_compose(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    scene = SceneDefinition(
        scene_id="s1",
        background="assets/space.png",
        duration=1,
        camera="center",
        objects=[
            SceneObjectDefinition(
                id="sun", image="assets/sun.png", x=10, y=10, z_index=1
            )
        ],
    )
    canvas = LayerManager().compose_scene(
        root, scene, resolve_image=resolve_layer_image
    )
    composed = tmp_path / "composed.png"
    canvas.convert("RGB").save(composed)
    dest = tmp_path / "frame.png"
    from app.features.renderer.camera_schemas import Viewport

    w, h = even_dimensions(*composed_size(composed))
    render_frame(
        source_image=composed,
        viewport=Viewport(x=0, y=0, width=float(w), height=float(h)),
        output_size=(w, h),
        dest=dest,
    )
    assert dest.is_file()
    with Image.open(dest) as frame:
        assert frame.size == (w, h)


def composed_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def test_load_manifest_with_layers(tmp_path: Path) -> None:
    root = _seed_layer_project(tmp_path)
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "scene_manifest.json").write_text(
        json.dumps(
            {
                "fps": 15,
                "scenes": [
                    {
                        "scene_id": "scene_01",
                        "background": "assets/space.png",
                        "duration": 3,
                        "camera": "pan_left",
                        "objects": [
                            {
                                "id": "sun",
                                "image": "sun.png",
                                "x": 10,
                                "y": 10,
                                "scale": 1.0,
                                "rotation": 0,
                                "z_index": 1,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = load_scene_manifest(root)
    assert manifest.scenes[0].is_layered() is True
    assert len(manifest.scenes[0].objects) == 1
