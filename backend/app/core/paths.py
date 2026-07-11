"""Runtime filesystem path helpers."""

from __future__ import annotations

from app.core.config import Settings


def ensure_runtime_directories(settings: Settings) -> None:
    """Create data-root subdirectories required at startup."""
    for path in (
        settings.data_root_path,
        settings.logs_dir,
        settings.projects_dir,
        settings.models_dir,
        settings.outputs_dir,
        settings.cache_dir,
        settings.backups_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
