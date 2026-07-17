"""Tests for backend/asset_processor (Phase 4.6 production pipeline)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow ``import asset_processor`` when tests run from backend/ or repo root.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from asset_processor import AssetProcessor  # noqa: E402
from asset_processor.config import AssetProcessorConfig  # noqa: E402
from asset_processor.exceptions import ImageLoadError, ValidationError  # noqa: E402
from asset_processor.image_resizer import ImageResizer  # noqa: E402

pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _cfg(tmp_path: Path, **kwargs: object) -> AssetProcessorConfig:
    return AssetProcessorConfig(
        raw_directory=tmp_path / "raw_assets",
        output_directory=tmp_path / "processed_assets",
        cache_directory=tmp_path / "cache",
        target_size=int(kwargs.get("target_size", 128)),
        use_stub_remover=True,
        remove_background=bool(kwargs.get("remove_background", True)),
    )


def _opaque_jpg(path: Path, *, size: tuple[int, int] = (200, 150)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, (255, 255, 255))
    for x in range(40, size[0] - 40):
        for y in range(30, size[1] - 30):
            img.putpixel((x, y), (0, 90, 200))
    img.save(path, format="JPEG", quality=95)
    return path


def _transparent_png(path: Path, *, size: tuple[int, int] = (80, 80)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(10, size[0] - 10):
        for y in range(10, size[1] - 10):
            img.putpixel((x, y), (255, 120, 0, 255))
    img.save(path)
    return path


def test_opaque_jpg(tmp_path: Path) -> None:
    raw = _opaque_jpg(tmp_path / "raw_assets" / "earth.jpg")
    proc = AssetProcessor(_cfg(tmp_path))
    result = proc.process(raw)
    assert result.cached is False
    assert result.processed_path.name == "earth.png"
    assert result.processed_path.is_file()
    assert result.processed_path.with_suffix(".json").is_file()
    assert result.metadata.background_removed is True
    assert result.metadata.width == 128
    assert result.metadata.height == 128
    with Image.open(result.processed_path) as im:
        assert im.mode == "RGBA"


def test_transparent_png(tmp_path: Path) -> None:
    raw = _transparent_png(tmp_path / "raw_assets" / "moon.png")
    proc = AssetProcessor(_cfg(tmp_path))
    result = proc.process(raw)
    assert result.processed_path.is_file()
    with Image.open(result.processed_path) as im:
        assert im.mode == "RGBA"
        assert im.size == (128, 128)


def test_large_image(tmp_path: Path) -> None:
    raw = _opaque_jpg(tmp_path / "raw_assets" / "large.jpg", size=(2000, 1200))
    proc = AssetProcessor(_cfg(tmp_path, target_size=256))
    result = proc.process(raw)
    assert result.metadata.width == 256
    assert result.metadata.height == 256


def test_small_image_padded(tmp_path: Path) -> None:
    raw = _opaque_jpg(tmp_path / "raw_assets" / "tiny.jpg", size=(40, 30))
    proc = AssetProcessor(_cfg(tmp_path, target_size=128))
    result = proc.process(raw)
    # Always padded to square target canvas.
    assert result.metadata.width == 128
    assert result.metadata.height == 128


def test_repeated_image_uses_cache(tmp_path: Path) -> None:
    raw = _opaque_jpg(tmp_path / "raw_assets" / "sun.jpg")
    proc = AssetProcessor(_cfg(tmp_path))
    first = proc.process(raw)
    second = proc.process(raw)
    assert first.cached is False
    assert second.cached is True
    assert second.metadata.hash == first.metadata.hash


def test_corrupted_image(tmp_path: Path) -> None:
    bad = tmp_path / "raw_assets" / "broken.png"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"not-a-real-image")
    proc = AssetProcessor(_cfg(tmp_path))
    with pytest.raises(ImageLoadError):
        proc.process(bad)


def test_process_directory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw_assets"
    _opaque_jpg(raw_dir / "a.jpg")
    _transparent_png(raw_dir / "b.png")
    proc = AssetProcessor(_cfg(tmp_path))
    results = proc.process_directory(raw_dir)
    assert len(results) == 2
    names = {r.processed_path.name for r in results}
    assert names == {"a.png", "b.png"}


def test_resizer_centers_with_transparent_padding() -> None:
    resizer = ImageResizer(target_size=100)
    img = Image.new("RGBA", (50, 20), (255, 0, 0, 255))
    out = resizer.resize(img)
    assert out.size == (100, 100)
    # Corners should be transparent padding.
    assert out.getpixel((0, 0))[3] == 0
    # Center should contain the red subject.
    cx, cy = 50, 50
    assert out.getpixel((cx, cy))[0] > 200
