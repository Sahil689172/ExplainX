"""Video export layout and metadata JSON."""

from __future__ import annotations

import json
from pathlib import Path

from image_generation.logger import get_engine_logger
from video_renderer.encoder_metadata import VideoMetadata


class VideoExporter:
    """Export encoded videos to ``output/videos/<scene_name>/``."""

    def __init__(self, *, logger=None) -> None:
        self._log = logger or get_engine_logger("video_renderer")

    def scene_video_dir(self, base_dir: str | Path, scene_name: str) -> Path:
        safe = self._slugify(scene_name)
        return Path(base_dir) / "videos" / safe

    def export_metadata(self, metadata: VideoMetadata, output_dir: str | Path) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "metadata.json"
        path.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
        self._log.info("VIDEO_EXPORTED metadata=%s", path)
        return str(path)

    @staticmethod
    def _slugify(name: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in name.strip()).strip("_") or "scene"
