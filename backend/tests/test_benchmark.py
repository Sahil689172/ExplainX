"""Unit tests for passive BenchmarkTimer."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.benchmark import BenchmarkTimer


def test_benchmark_timer_start_stop_and_summary(capsys) -> None:
    bench = BenchmarkTimer()
    bench.start("total_pipeline")
    bench.start("project_creation")
    bench.stop("project_creation")
    bench.record("ingestion", 0.04)
    bench.record("script_generation", 1.23)
    bench.record("translation", 0.0)
    bench.record("audio_generation", 0.0)
    bench.stop("total_pipeline")
    bench.set_meta(language="en", llm_model="qwen2.5:3b")

    data = bench.to_dict()
    assert data["project_creation"] >= 0.0
    assert data["ingestion"] == 0.04
    assert data["translation"] == 0.0
    assert data["language"] == "en"
    assert "timestamp" in data

    bench.summary()
    out = capsys.readouterr().out
    assert "BENCHMARK" in out
    assert "TOTAL :" in out


def test_benchmark_save_json(tmp_path: Path) -> None:
    bench = BenchmarkTimer()
    bench.record("project_creation", 0.18)
    bench.record("ingestion", 0.04)
    bench.record("script_generation", 47.63)
    bench.record("translation", 3.81)
    bench.record("audio_generation", 41.72)
    bench.record("total_pipeline", 93.38)
    bench.set_meta(
        language="hi",
        llm_model="qwen2.5:3b",
        tts_provider="Piper",
        voice="hi_IN-pratham-medium",
    )
    path = bench.save(tmp_path / "benchmark.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["translation"] == 3.81
    assert loaded["voice"] == "hi_IN-pratham-medium"
