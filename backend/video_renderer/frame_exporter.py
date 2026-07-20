"""Export rendered frames to disk with zero-padded naming."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from image_generation.logger import get_engine_logger


class FrameExporter:
    """Write PNG frames to ``output/frames/<scene_name>/frame_NNNNNN.png``."""

    def __init__(self, *, pad_width: int = 6, logger=None) -> None:
        self._pad = pad_width
        self._log = logger or get_engine_logger("video_renderer")

    def scene_output_dir(self, base_dir: str | Path, scene_name: str) -> Path:
        safe = self._slugify(scene_name)
        return Path(base_dir) / "frames" / safe

    def export(
        self,
        image: Image.Image,
        output_dir: str | Path,
        export_index: int,
    ) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        filename = f"frame_{export_index:0{self._pad}d}.png"
        path = out / filename
        image.save(path, format="PNG")
        self._log.info("FRAME_EXPORTED path=%s index=%s", path, export_index)
        return str(path)

    @staticmethod
    def _slugify(name: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in name.strip()).strip("_") or "scene"
