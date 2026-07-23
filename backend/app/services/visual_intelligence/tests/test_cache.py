"""Unit tests for the SHA256 AssetCache and AssetRepository."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.services.visual_intelligence.cache import AssetCache, compute_hash
from app.services.visual_intelligence.repository import AssetRepository
from app.services.visual_intelligence.schemas import RendererType, RenderRequest


def _png(path: Path, color=(20, 40, 60)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), color).save(path)
    return path


def _request(**kwargs) -> RenderRequest:
    base = dict(prompt="a cell diagram", model="sd15", renderer=RendererType.OPENVINO, seed=7)
    base.update(kwargs)
    return RenderRequest(**base)


def test_hash_is_stable_and_order_independent():
    a = _request(parameters={"steps": 20, "cfg": 7.5})
    b = _request(parameters={"cfg": 7.5, "steps": 20})
    assert compute_hash(a) == compute_hash(b)


def test_hash_changes_with_seed():
    assert compute_hash(_request(seed=1)) != compute_hash(_request(seed=2))


def test_hash_changes_with_renderer():
    assert compute_hash(_request(renderer=RendererType.OPENVINO)) != compute_hash(
        _request(renderer=RendererType.SVG)
    )


def test_store_and_lookup_roundtrip(tmp_path):
    cache = AssetCache(tmp_path / "cache")
    src = _png(tmp_path / "src.png")
    req = _request()
    record = cache.store(req, png_path=src, generation_time_sec=1.25)
    assert record.hash == compute_hash(req)
    assert Path(record.asset_path).is_file()
    assert record.thumbnail_path and Path(record.thumbnail_path).is_file()
    assert record.width == 64 and record.height == 48

    found = cache.lookup(req)
    assert found is not None
    assert found.hash == record.hash
    assert found.generation_time_sec == 1.25


def test_get_or_create_produces_then_caches(tmp_path):
    cache = AssetCache(tmp_path / "cache")
    req = _request()
    calls = {"n": 0}

    def producer(entry: Path):
        calls["n"] += 1
        _png(entry / "asset.png", color=(200, 10, 10))
        return {"generation_time_sec": 0.4}

    record1, cached1 = cache.get_or_create(req, producer)
    record2, cached2 = cache.get_or_create(req, producer)

    assert cached1 is False
    assert cached2 is True
    assert calls["n"] == 1  # producer only ran once
    assert record1.hash == record2.hash


def test_repository_find_exists_register(tmp_path):
    repo = AssetRepository(tmp_path / "cache")
    req = _request(prompt="unique-prompt")
    assert repo.exists(req) is False
    assert repo.find(req) is None

    src = _png(tmp_path / "img.png")
    record = repo.register(req, png_path=src, generation_time_sec=0.9)
    assert repo.exists(req) is True
    assert repo.find(req).hash == record.hash


def test_repository_list_and_stats(tmp_path):
    repo = AssetRepository(tmp_path / "cache")
    repo.register(_request(prompt="a"), png_path=_png(tmp_path / "a.png"))
    repo.register(
        _request(prompt="b", renderer=RendererType.SVG), png_path=_png(tmp_path / "b.png")
    )
    all_records = repo.list_all()
    assert len(all_records) == 2
    stats = repo.stats()
    assert stats["total_assets"] == 2
    assert stats["by_renderer"].get("svg") == 1


def test_repository_svg_stored(tmp_path):
    repo = AssetRepository(tmp_path / "cache")
    png = _png(tmp_path / "c.png")
    svg = tmp_path / "c.svg"
    svg.write_text("<svg></svg>", encoding="utf-8")
    record = repo.register(_request(renderer=RendererType.SVG), png_path=png, svg_path=svg)
    assert record.svg_path and Path(record.svg_path).is_file()
