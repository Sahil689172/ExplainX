"""RenderService — static image or multi-scene → frames → video.mp4."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.renderer.artifacts import RenderArtifactStore
from app.features.renderer.camera_service import CameraService
from app.features.renderer.exporter import export_video, resolve_ffmpeg_executable
from app.features.renderer.frame_renderer import (
    discover_input_image,
    even_dimensions,
    generate_camera_frames,
    read_image_resolution,
)
from app.features.renderer.scene_service import SceneComposer
from app.features.renderer.schemas import RenderConfig, RenderMetadata

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Outcome of one render run."""

    project_id: str
    input_image: Path
    video_path: Path
    metadata_path: Path
    metadata: RenderMetadata
    camera_metadata_path: Path | None = None
    scene_metadata_path: Path | None = None
    multi_scene: bool = False


class RenderService:
    """Renderer: camera viewport per frame → FFmpeg video."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._store = RenderArtifactStore(self._fs)

    def build_config(self) -> RenderConfig:
        fmt = (self._settings.frame_output_format or "png").strip().lower().lstrip(".")
        return RenderConfig(
            fps=int(self._settings.render_fps),
            duration_sec=int(self._settings.default_duration_seconds),
            frame_format=fmt,
        )

    def render(self, project_id: str) -> RenderResult:
        """Generate frames + video.mp4 for ``project_id``."""
        validate_project_id(project_id)
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )

        project_root = self._fs.project_root(project_id)
        config = self.build_config()
        if SceneComposer.is_enabled(project_root):
            return self._render_scenes(project_id, project_root, config)
        return self._render_single(project_id, project_root, config)

    def _render_single(
        self,
        project_id: str,
        project_root: Path,
        config: RenderConfig,
    ) -> RenderResult:
        """Phase 2 — single image + project/settings camera."""
        input_image = discover_input_image(project_root)
        width, height = even_dimensions(*read_image_resolution(input_image))
        output_size = (width, height)

        camera = CameraService.from_project(
            project_root,
            self._settings,
            duration_sec=config.duration_sec,
            image_width=width,
            image_height=height,
        )
        camera.log_camera()

        ffmpeg_exe = resolve_ffmpeg_executable(
            self._settings.ffmpeg_executable,
            repo_root=_REPO_ROOT,
        )

        started = time.perf_counter()
        frames_dir = self._store.frames_dir(project_id)
        frame_count = generate_camera_frames(
            source_image=input_image,
            frames_dir=frames_dir,
            config=config,
            camera=camera,
            output_size=output_size,
        )
        video_path = export_video(
            frames_dir=frames_dir,
            output_video=self._store.video_path(project_id),
            config=config,
            ffmpeg_executable=ffmpeg_exe,
        )
        render_time = time.perf_counter() - started

        metadata = RenderMetadata(
            fps=config.fps,
            duration=config.duration_sec,
            frame_count=frame_count,
            resolution=f"{width}x{height}",
            render_time=round(render_time, 2),
            input_image=input_image.name,
            output_video=video_path.name,
        )
        metadata_path = self._write_metadata(project_id, metadata)
        camera_metadata_path = self._write_camera_metadata(project_id, camera)

        self._log_render(
            input_image=input_image.name,
            config=config,
            frame_count=frame_count,
            resolution=metadata.resolution,
            render_time=metadata.render_time,
            output_video=video_path.name,
        )

        logger.info(
            "Render completed (single scene)",
            extra={
                "event": "render_completed",
                "project_id": project_id,
                "frame_count": frame_count,
                "render_time_sec": metadata.render_time,
                "camera_type": camera.config.type.value,
            },
        )
        return RenderResult(
            project_id=project_id,
            input_image=input_image,
            video_path=video_path,
            metadata_path=metadata_path,
            metadata=metadata,
            camera_metadata_path=camera_metadata_path,
            multi_scene=False,
        )

    def _render_scenes(
        self,
        project_id: str,
        project_root: Path,
        config: RenderConfig,
    ) -> RenderResult:
        """Phase 3 — multi-scene manifest → concatenated frames → video."""
        started = time.perf_counter()
        composer = SceneComposer(settings=self._settings, store=self._store)
        compose = composer.compose(project_id, project_root, base_config=config)

        export_config = RenderConfig(
            fps=compose.metadata.fps,
            duration_sec=compose.metadata.video_duration,
            frame_format=config.frame_format,
        )
        ffmpeg_exe = resolve_ffmpeg_executable(
            self._settings.ffmpeg_executable,
            repo_root=_REPO_ROOT,
        )

        frames_dir = self._store.frames_dir(project_id)
        video_path = export_video(
            frames_dir=frames_dir,
            output_video=self._store.video_path(project_id),
            config=export_config,
            ffmpeg_executable=ffmpeg_exe,
        )
        render_time = time.perf_counter() - started

        out_w, out_h = compose.output_size
        metadata = RenderMetadata(
            fps=compose.metadata.fps,
            duration=compose.metadata.video_duration,
            frame_count=compose.total_frames,
            resolution=f"{out_w}x{out_h}",
            render_time=round(render_time, 2),
            input_image=compose.first_image.name,
            output_video=video_path.name,
        )
        metadata_path = self._write_metadata(project_id, metadata)
        scene_metadata_path = self._write_scene_metadata(project_id, compose.metadata)

        self._log_render(
            input_image=compose.first_image.name,
            config=export_config,
            frame_count=compose.total_frames,
            resolution=metadata.resolution,
            render_time=metadata.render_time,
            output_video=video_path.name,
        )

        logger.info(
            "Render completed (multi-scene)",
            extra={
                "event": "render_completed",
                "project_id": project_id,
                "scene_count": compose.metadata.scene_count,
                "frame_count": compose.total_frames,
                "render_time_sec": metadata.render_time,
            },
        )
        return RenderResult(
            project_id=project_id,
            input_image=compose.first_image,
            video_path=video_path,
            metadata_path=metadata_path,
            metadata=metadata,
            scene_metadata_path=scene_metadata_path,
            multi_scene=True,
        )

    def _write_metadata(self, project_id: str, metadata: RenderMetadata) -> Path:
        path = self._store.metadata_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(metadata.model_dump(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def _write_camera_metadata(self, project_id: str, camera: CameraService) -> Path:
        path = self._store.camera_metadata_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(camera.metadata().model_dump(), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        return path

    def _write_scene_metadata(self, project_id: str, metadata: object) -> Path:
        path = self._store.scene_metadata_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(metadata, "model_dump"):
            payload = metadata.model_dump()
        else:
            payload = metadata
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _log_render(
        *,
        input_image: str,
        config: RenderConfig,
        frame_count: int,
        resolution: str,
        render_time: float,
        output_video: str,
    ) -> None:
        print("[Renderer]", flush=True)
        print(f"Input Image : {input_image}", flush=True)
        print(f"FPS : {config.fps}", flush=True)
        print(f"Duration : {config.duration_sec} sec", flush=True)
        print(f"Frames : {frame_count}", flush=True)
        print(f"Resolution : {resolution}", flush=True)
        print(f"Render Time : {render_time:.1f} sec", flush=True)
        print(f"Output : {output_video}", flush=True)
