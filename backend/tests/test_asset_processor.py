"""Tests for Phase 4.6 — Asset Processing Pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ValidationAppError
from app.features.asset_processor import AssetProcessor
from app.features.asset_processor.asset_validator import AssetValidator
from app.features.asset_processor.background_remover import BackgroundRemover
from app.features.asset_processor.image_normalizer import ImageNormalizer
from app.features.asset_processor.image_resizer import ImageResizer

pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _processor(tmp_path: Path, **kwargs: object) -> AssetProcessor:
    return AssetProcessor(
        raw_dir=tmp_path / "raw_assets",
        processed_dir=tmp_path / "processed_assets",
        cache_dir=tmp_path / "cache",
        model_dir=tmp_path / "models",
        target_size=int(kwargs.get("target_size", 512)),
        stub_background_removal=True,
        remove_background=bool(kwargs.get("remove_background", True)),
    )


def _opaque_white_bg(path: Path, *, size: tuple[int, int] = (200, 150)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, (255, 255, 255))
    # Draw a blue square in the center (subject).
    for x in range(60, 140):
        for y in range(40, 110):
            img.putpixel((x, y), (0, 80, 200))
    img.save(path)
    return path


def _transparent_png(path: Path, *, size: tuple[int, int] = (100, 100)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(20, 80):
        for y in range(20, 80):
            img.putpixel((x, y), (255, 100, 0, 255))
    img.save(path)
    return path


def test_opaque_image_becomes_transparent_png(tmp_path: Path) -> None:
    raw = _opaque_white_bg(tmp_path / "raw_assets" / "earth.jpg")
    proc = _processor(tmp_path)
    result = proc.process(raw)

    assert result.cached is False
    assert result.processed_path.suffix.lower() == ".png"
    assert result.processed_path.is_file()
    assert result.metadata.background_removed is True
    assert result.metadata.transparent is True

    with Image.open(result.processed_path) as im:
        assert im.mode == "RGBA"
        alpha = im.getchannel("A")
        assert min(alpha.getextrema()) < 255


def test_transparent_png_roundtrip(tmp_path: Path) -> None:
    raw = _transparent_png(tmp_path / "raw_assets" / "moon.png")
    proc = _processor(tmp_path)
    result = proc.process(raw)
    assert result.processed_path.is_file()
    with Image.open(result.processed_path) as im:
        assert im.mode == "RGBA"


def test_repeated_image_uses_cache(tmp_path: Path) -> None:
    raw = _opaque_white_bg(tmp_path / "raw_assets" / "sun.png")
    proc = _processor(tmp_path)
    first = proc.process(raw)
    second = proc.process(raw)
    assert first.cached is False
    assert second.cached is True
    assert second.metadata.hash == first.metadata.hash
    assert second.processed_path.is_file()


def test_large_image_fits_target_size(tmp_path: Path) -> None:
    raw = _opaque_white_bg(tmp_path / "raw_assets" / "large.png", size=(2000, 1200))
    proc = _processor(tmp_path, target_size=512)
    result = proc.process(raw)
    assert result.metadata.width <= 512
    assert result.metadata.height <= 512
    assert max(result.metadata.width, result.metadata.height) == 512


def test_small_image_not_upscaled(tmp_path: Path) -> None:
    raw = _opaque_white_bg(tmp_path / "raw_assets" / "tiny.png", size=(40, 30))
    proc = _processor(tmp_path, target_size=512)
    result = proc.process(raw)
    # Stub may crop via alpha but dimensions stay <= original contain-fit.
    assert result.metadata.width <= 40 or result.metadata.height <= 30
    assert max(result.metadata.width, result.metadata.height) <= 512


def test_corrupted_image_raises(tmp_path: Path) -> None:
    bad = tmp_path / "raw_assets" / "broken.png"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"not-an-image")
    proc = _processor(tmp_path)
    with pytest.raises(ValidationAppError) as exc:
        proc.process(bad)
    assert exc.value.code == "ASSET_CORRUPTED"


def test_resizer_preserves_aspect_ratio() -> None:
    resizer = ImageResizer(target_size=100)
    img = Image.new("RGBA", (400, 200), (1, 2, 3, 255))
    out = resizer.resize(img)
    assert out.size == (100, 50)


def test_normalizer_outputs_rgba() -> None:
    img = Image.new("RGB", (16, 16), (10, 20, 30))
    out = ImageNormalizer().normalize(img)
    assert out.mode == "RGBA"


def test_validator_rejects_non_rgba(tmp_path: Path) -> None:
    path = tmp_path / "rgb.png"
    Image.new("RGB", (32, 32), (1, 1, 1)).save(path)
    with pytest.raises(ValidationAppError) as exc:
        AssetValidator().validate_processed(path)
    assert exc.value.code == "ASSET_NOT_RGBA"


def test_stub_background_remover() -> None:
    img = Image.new("RGB", (50, 50), (255, 255, 255))
    for x in range(15, 35):
        for y in range(15, 35):
            img.putpixel((x, y), (255, 0, 0))
    out = BackgroundRemover(Path("."), stub=True).remove(img)
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((25, 25))[3] == 255


def test_from_data_root_creates_folders(tmp_path: Path) -> None:
    proc = AssetProcessor.from_data_root(tmp_path, stub_background_removal=True)
    assert proc.raw_dir.is_dir()
    assert proc.processed_dir.is_dir()
    assert proc.cache_dir.is_dir()
