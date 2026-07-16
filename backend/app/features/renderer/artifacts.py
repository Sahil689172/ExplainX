"""Renderer artifact paths."""

from __future__ import annotations

from pathlib import Path

from app.features.projects.filesystem import ProjectFilesystem, validate_project_id


class RenderArtifactStore:
    """Paths under ``artifacts/`` for renderer MVP output."""

    def __init__(self, filesystem: ProjectFilesystem) -> None:
        self._fs = filesystem

    def artifacts_dir(self, project_id: str) -> Path:
        validate_project_id(project_id)
        return self._fs.project_root(project_id) / "artifacts"

    def frames_dir(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "frames"

    def video_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "video.mp4"

    def metadata_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "render_metadata.json"

    def camera_metadata_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "camera_metadata.json"

    def scene_metadata_path(self, project_id: str) -> Path:
        return self.artifacts_dir(project_id) / "scene_metadata.json"

    def frame_path(self, project_id: str, index: int, *, ext: str) -> Path:
        return self.frames_dir(project_id) / f"{index:06d}.{ext.lstrip('.')}"
