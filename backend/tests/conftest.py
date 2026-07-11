"""Pytest configuration for backend tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import reset_settings_cache


@pytest.fixture(autouse=True)
def _test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("EXPLAINX_ENV", "testing")
    monkeypatch.setenv("EXPLAINX_DATA_ROOT", str(data_root))
    monkeypatch.setenv("EXPLAINX_LOG_TO_FILE", "false")
    monkeypatch.setenv("EXPLAINX_DEBUG", "true")
    reset_settings_cache()
    yield
    reset_settings_cache()
