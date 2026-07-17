"""SceneComposer — render multiple scenes into one continuous video."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.features.renderer.artifacts import RenderArtifactStore
from app.features.renderer.camera_service import CameraService
from app.features.renderer.frame_renderer import (
    even_dimensions,
    generate_camera_frames_segment,
    read_image_resolution,
)
from app.features.renderer.scene import (
    camera_label,
    log_scene,
    scene_frame_count,
    total_frame_count,
)
from app.features.renderer.scene_manifest import (
    load_scene_manifest,
    manifest_exists,
    ordered_scenes,
    resolve_scene_image,
)
from app.features.renderer.scene_schemas import SceneMetadata, SceneRenderRecord
from app.features.renderer.schemas import RenderConfig


@dataclass(frozen=True, slots=True)
class SceneComposeResult:
    """Outcome of a multi-scene render."""

    output_size: tuple[int, int]
    total_frames: int
    metadata: SceneMetadata
    first_image: Path


class SceneComposer:
    """Render each manifest scene sequentially into one frame sequence."""

    def __init__(self, *, settings: Settings, store: RenderArtifactStore) -> None:
        self._settings = settings
        self._store = store

    @staticmethod
    def is_enabled(project_root: Path) -> bool:
        return manifest_exists(project_root)

    def compose(
        self,
        project_id: str,
        project_root: Path,
        *,
        base_config: RenderConfig,
    ) -> SceneComposeResult:
        manifest = load_scene_manifest(project_root)
        fps = int(manifest.fps or base_config.fps)
        fmt = base_config.frame_format
        scenes = ordered_scenes(manifest)

        first_image = resolve_scene_image(project_root, scenes[0].image)
        out_w, out_h = even_dimensions(*read_image_resolution(first_image))
        output_size = (out_w, out_h)

        frames_dir = self._store.frames_dir(project_id)
        ext = fmt.lower().lstrip(".")
        frames_dir.mkdir(parents=True, exist_ok=True)
        for old in frames_dir.glob(f"*.{ext}"):
            old.unlink()

        global_index = 1
        records: list[SceneRenderRecord] = []
        durations: list[int] = []
        frames_per_scene: list[int] = []
        cameras_used: list[str] = []

        for scene_index, scene in enumerate(scenes, start=1):
            image_path = resolve_scene_image(project_root, scene.image)
            img_w, img_h = read_image_resolution(image_path)
            if (img_w, img_h) != output_size:
                # Output size is fixed to the first scene; render_frame scales each crop.
                pass

            camera_config = scene.to_camera_config()
            camera = CameraService.from_config(
                config=camera_config,
                image_width=img_w,
                image_height=img_h,
            )
            segment_frames = scene_frame_count(duration_sec=scene.duration, fps=fps)
            log_scene(
                index=scene_index,
                total=len(scenes),
                scene=scene,
                frames=segment_frames,
            )

            written = generate_camera_frames_segment(
                source_image=image_path,
                frames_dir=frames_dir,
                fps=fps,
                duration_sec=scene.duration,
                frame_format=fmt,
                camera=camera,
                output_size=output_size,
                frame_start_index=global_index,
            )
            if written != segment_frames:
                raise RuntimeError(
                    f"Scene {scene.scene_id} frame mismatch: "
                    f"expected {segment_frames}, wrote {written}"
                )

            records.append(
                SceneRenderRecord(
                    scene_id=scene.scene_id,
                    image=scene.image,
                    duration_seconds=scene.duration,
                    frames=segment_frames,
                    camera=scene.camera.value,
                )
            )
            durations.append(scene.duration)
            frames_per_scene.append(segment_frames)
            cameras_used.append(camera_label(scene.camera))
            global_index += segment_frames

        total_frames = global_index - 1
        video_duration = sum(durations)
        metadata = SceneMetadata(
            scene_count=len(scenes),
            scene_duration=durations,
            frames_per_scene=frames_per_scene,
            camera_used=cameras_used,
            total_frames=total_frames,
            fps=fps,
            video_duration=video_duration,
            scenes=records,
        )
        return SceneComposeResult(
            output_size=output_size,
            total_frames=total_frames,
            metadata=metadata,
            first_image=first_image,
        )
