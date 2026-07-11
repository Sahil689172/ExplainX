"""Pytest configuration for backend tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import reset_settings_cache
from app.db.bootstrap import init_database
from app.db.session import reset_db_engine
from app.main import create_app


@pytest.fixture(autouse=True)
def _test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("EXPLAINX_ENV", "testing")
    monkeypatch.setenv("EXPLAINX_DATA_ROOT", str(data_root))
    monkeypatch.setenv("EXPLAINX_LOG_TO_FILE", "false")
    monkeypatch.setenv("EXPLAINX_DEBUG", "true")
    # Force sqlite under tmp data root
    monkeypatch.delenv("EXPLAINX_DATABASE_URL", raising=False)
    reset_settings_cache()
    reset_db_engine()
    init_database()
    yield data_root
    reset_db_engine()
    reset_settings_cache()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app()) as test_client:
        yield test_client
