"""ExplainX Asset Cache — content-addressed, reusable generated assets.

The cache key is a SHA256 over the request's ``prompt``, ``model``,
``parameters``, ``renderer`` and ``seed``. Identical requests return the cached
asset; new requests are stored with a PNG (and optional SVG), a JSON metadata
sidecar, a thumbnail, creation date, renderer, and generation time.

This module never renders — a caller passes an already-produced asset (or a
producer callable) to :meth:`AssetCache.get_or_create`. It does not modify the
rendering engine.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.services.visual_intelligence.schemas import AssetRecord, RenderRequest


def compute_hash(request: RenderRequest) -> str:
    """SHA256 of the canonical request description."""
    return hashlib.sha256(request.canonical().encode("utf-8")).hexdigest()


class AssetCache:
    """Content-addressed asset store under ``<cache_dir>/<ab>/<hash>/``."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- layout ---------------------------------------------------------- #

    def entry_dir(self, digest: str) -> Path:
        return self.cache_dir / digest[:2] / digest

    def _paths(self, digest: str) -> dict[str, Path]:
        base = self.entry_dir(digest)
        return {
            "dir": base,
            "png": base / "asset.png",
            "svg": base / "asset.svg",
            "thumb": base / "thumbnail.png",
            "meta": base / "metadata.json",
        }

    # ---- lookup ---------------------------------------------------------- #

    def has(self, digest: str) -> bool:
        p = self._paths(digest)
        return p["meta"].is_file() and p["png"].is_file()

    def lookup(self, request: RenderRequest) -> AssetRecord | None:
        digest = compute_hash(request)
        return self.load(digest)

    def load(self, digest: str) -> AssetRecord | None:
        p = self._paths(digest)
        if not p["meta"].is_file():
            return None
        try:
            data = json.loads(p["meta"].read_text(encoding="utf-8"))
            return AssetRecord.model_validate(data)
        except (OSError, ValueError):
            return None

    # ---- store ----------------------------------------------------------- #

    def store(
        self,
        request: RenderRequest,
        *,
        png_path: str | Path,
        svg_path: str | Path | None = None,
        thumbnail_path: str | Path | None = None,
        generation_time_sec: float = 0.0,
        width: int | None = None,
        height: int | None = None,
    ) -> AssetRecord:
        """Copy a produced asset into the cache and write its metadata record."""
        digest = compute_hash(request)
        p = self._paths(digest)
        p["dir"].mkdir(parents=True, exist_ok=True)

        src_png = Path(png_path)
        if not src_png.is_file():
            raise FileNotFoundError(f"PNG asset not found: {src_png}")
        if src_png.resolve() != p["png"].resolve():
            shutil.copy2(src_png, p["png"])

        stored_svg: str | None = None
        if svg_path and Path(svg_path).is_file():
            if Path(svg_path).resolve() != p["svg"].resolve():
                shutil.copy2(svg_path, p["svg"])
            stored_svg = str(p["svg"])

        stored_thumb: str | None = None
        if thumbnail_path and Path(thumbnail_path).is_file():
            if Path(thumbnail_path).resolve() != p["thumb"].resolve():
                shutil.copy2(thumbnail_path, p["thumb"])
            stored_thumb = str(p["thumb"])
        else:
            stored_thumb = self._make_thumbnail(p["png"], p["thumb"])

        if width is None or height is None:
            width, height = self._image_size(p["png"])

        record = AssetRecord(
            hash=digest,
            renderer=request.renderer,
            prompt=request.prompt,
            model=request.model,
            seed=request.seed,
            parameters=request.parameters,
            asset_path=str(p["png"]),
            svg_path=stored_svg,
            thumbnail_path=stored_thumb,
            metadata_path=str(p["meta"]),
            created_at=datetime.now(timezone.utc).isoformat(),
            generation_time_sec=round(generation_time_sec, 4),
            width=width,
            height=height,
        )
        p["meta"].write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return record

    def get_or_create(
        self,
        request: RenderRequest,
        producer: Callable[[Path], dict[str, object]],
    ) -> tuple[AssetRecord, bool]:
        """Return a cached asset, or produce+store a new one.

        ``producer`` receives the entry directory and must write an
        ``asset.png`` (at minimum). It may return a dict with optional keys
        ``svg_path``, ``thumbnail_path``, ``generation_time_sec``, ``width``,
        ``height``. Returns ``(record, was_cached)``.

        This is the only generation seam; the cache still never renders itself.
        """
        cached = self.lookup(request)
        if cached is not None:
            return cached, True

        digest = compute_hash(request)
        entry = self.entry_dir(digest)
        entry.mkdir(parents=True, exist_ok=True)
        result = producer(entry) or {}

        png = result.get("png_path") or (entry / "asset.png")
        record = self.store(
            request,
            png_path=png,
            svg_path=result.get("svg_path"),
            thumbnail_path=result.get("thumbnail_path"),
            generation_time_sec=float(result.get("generation_time_sec", 0.0) or 0.0),
            width=result.get("width"),
            height=result.get("height"),
        )
        return record, False

    # ---- helpers --------------------------------------------------------- #

    @staticmethod
    def _make_thumbnail(png: Path, dest: Path, size: int = 256) -> str | None:
        try:
            from PIL import Image

            with Image.open(png) as img:
                img = img.convert("RGBA")
                img.thumbnail((size, size), Image.LANCZOS)
                img.save(dest)
            return str(dest)
        except Exception:  # noqa: BLE001 — thumbnails are best-effort
            return None

    @staticmethod
    def _image_size(png: Path) -> tuple[int | None, int | None]:
        try:
            from PIL import Image

            with Image.open(png) as img:
                return img.width, img.height
        except Exception:  # noqa: BLE001
            return None, None
