"""SceneComposer — render multiple scenes into one continuous video."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.features.renderer.artifacts import RenderArtifactStore
from app.features.renderer.asset_quality import (
    AssetInfo,
    inspect_asset,
    log_asset,
    log_renderer_output,
)
from app.features.renderer.camera_service import CameraService
from app.features.renderer.diagnostics import (
    RenderDiagnostics,
    SceneDiagnostic,
)
from app.features.renderer.frame_renderer import (
    even_dimensions,
    generate_camera_frames_segment,
    read_image_resolution,
)
from app.features.renderer.layers.layer_manager import LayerManager
from app.features.renderer.scene import (
    camera_label,
    log_scene,
    scene_frame_count,
)
from app.features.renderer.scene_manifest import (
    load_scene_manifest,
    manifest_exists,
    ordered_scenes,
    resolve_layer_image,
    resolve_scene_image,
)
from app.features.renderer.scene_schemas import (
    SceneDefinition,
    SceneMetadata,
    SceneRenderRecord,
)
from app.features.renderer.schemas import RenderConfig


@dataclass(frozen=True, slots=True)
class SceneComposeResult:
    """Outcome of a multi-scene render."""

    output_size: tuple[int, int]
    total_frames: int
    metadata: SceneMetadata
    first_image: Path
    diagnostics: RenderDiagnostics


class SceneComposer:
    """Render each manifest scene sequentially into one frame sequence."""

    def __init__(self, *, settings: Settings, store: RenderArtifactStore) -> None:
        self._settings = settings
        self._store = store
        self._layers = LayerManager()

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

        # Fixed export resolution (Phase 4.5) — independent of scene canvas size.
        out_w, out_h = even_dimensions(
            int(self._settings.output_width),
            int(self._settings.output_height),
        )
        output_size = (out_w, out_h)
        log_renderer_output(out_w, out_h)

        first_source = self._scene_source_image(project_root, scenes[0])
        scene_w, scene_h = read_image_resolution(first_source)

        frames_dir = self._store.frames_dir(project_id)
        ext = fmt.lower().lstrip(".")
        frames_dir.mkdir(parents=True, exist_ok=True)
        for old in frames_dir.glob(f"*.{ext}"):
            old.unlink()

        compose_dir = frames_dir.parent / "composed"
        compose_dir.mkdir(parents=True, exist_ok=True)

        global_index = 1
        records: list[SceneRenderRecord] = []
        durations: list[int] = []
        frames_per_scene: list[int] = []
        cameras_used: list[str] = []
        scene_diags: list[SceneDiagnostic] = []
        all_assets: list[AssetInfo] = []
        warnings: list[str] = []
        camera_smoothing = "ease_in_out"

        for scene_index, scene in enumerate(scenes, start=1):
            image_path, asset_infos = self._prepare_scene_image(
                project_root=project_root,
                scene=scene,
                compose_dir=compose_dir,
            )
            all_assets.extend(asset_infos)
            for info in asset_infos:
                warnings.extend(info.warnings)

            img_w, img_h = read_image_resolution(image_path)
            camera_config = scene.to_camera_config(
                default_zoom=float(self._settings.default_zoom),
            )
            camera_smoothing = camera_config.easing
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

            # Always crop from the ORIGINAL composed/source image for this scene.
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
                    image=scene.primary_image_ref(),
                    duration_seconds=scene.duration,
                    frames=segment_frames,
                    camera=scene.camera.value,
                    object_count=len(scene.objects),
                    layered=scene.is_layered(),
                )
            )
            scene_diags.append(
                SceneDiagnostic(
                    scene_id=scene.scene_id,
                    scene_resolution=f"{img_w}x{img_h}",
                    camera_type=scene.camera.value,
                    camera_easing=camera_config.easing,
                    camera_start_scale=camera_config.start_scale,
                    camera_end_scale=camera_config.end_scale,
                    layered=scene.is_layered(),
                    object_count=len(scene.objects),
                    assets=[RenderDiagnostics.from_asset(a) for a in asset_infos],
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
        diagnostics = RenderDiagnostics(
            output_resolution=f"{out_w}x{out_h}",
            scene_resolution=f"{scene_w}x{scene_h}",
            camera_smoothing=camera_smoothing,
            scenes=scene_diags,
            assets=[RenderDiagnostics.from_asset(a) for a in all_assets],
            warnings=warnings,
        )
        return SceneComposeResult(
            output_size=output_size,
            total_frames=total_frames,
            metadata=metadata,
            first_image=first_source,
            diagnostics=diagnostics,
        )

    def _scene_source_image(
        self, project_root: Path, scene: SceneDefinition
    ) -> Path:
        """Return a path usable for resolution probing (background or legacy image)."""
        if scene.is_layered():
            return resolve_layer_image(project_root, scene.background_ref())
        return resolve_scene_image(project_root, scene.background_ref())

    def _prepare_scene_image(
        self,
        *,
        project_root: Path,
        scene: SceneDefinition,
        compose_dir: Path,
    ) -> tuple[Path, list[AssetInfo]]:
        """Legacy image path, or compose background+objects once for the scene."""
        if not scene.is_layered():
            path = resolve_scene_image(project_root, scene.background_ref())
            info = inspect_asset(path, label=path.name, role="background")
            log_asset(info)
            return path, [info]

        composed = self._layers.compose_scene(
            project_root,
            scene,
            resolve_image=resolve_layer_image,
        )
        out_path = compose_dir / f"{scene.scene_id}_composed.png"
        # Persist ORIGINAL composed scene; every camera frame crops from this file.
        composed.convert("RGB").save(out_path)
        return out_path, list(self._layers.last_asset_infos)
