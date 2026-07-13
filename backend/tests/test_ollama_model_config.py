"""Tests for configurable Ollama model selection via Settings."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import ExplainXError
from app.features.script.ollama.client import MODEL_NOT_INSTALLED, OllamaClient


def test_settings_field_defaults_match_contract() -> None:
    """Field defaults (not env) are the production contract."""
    assert Settings.model_fields["ollama_model"].default == "qwen2.5:3b"
    assert Settings.model_fields["ollama_timeout_sec"].default == 600.0
    assert Settings.model_fields["ollama_temperature"].default == 0.2
    assert Settings.model_fields["ollama_base_url"].default == "http://127.0.0.1:11434"


def test_client_from_settings_uses_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)
    monkeypatch.delenv("OLLAMA_TEMPERATURE", raising=False)
    settings = Settings(
        env="testing",
        ollama_model="custom-model:tag",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_timeout_sec=120.0,
        ollama_temperature=0.4,
        ollama_enabled=True,
    )
    client = OllamaClient.from_settings(settings)
    assert client.model == "custom-model:tag"
    assert client.temperature == 0.4
    assert client.timeout_sec == 120.0


def test_configured_model_exists() -> None:
    configured = "demo-model:latest"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": configured},
                        {"name": "other-model:1"},
                    ]
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    client = OllamaClient(
        base_url="http://ollama.test",
        model=configured,
        transport=httpx.MockTransport(handler),
    )
    installed = client.ensure_ready()
    assert configured in installed
    assert client.model_is_installed(installed) is True


def test_configured_model_missing() -> None:
    configured = "missing-model:9b"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "installed-a:latest"},
                        {"name": "installed-b:1"},
                    ]
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    client = OllamaClient(
        base_url="http://ollama.test",
        model=configured,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ExplainXError) as exc:
        client.ensure_ready()
    assert exc.value.code == MODEL_NOT_INSTALLED
    assert exc.value.details is not None
    assert exc.value.details["model"] == configured
    assert "installed-a:latest" in exc.value.details["installed_models"]


def test_generate_uses_settings_temperature_and_model() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return httpx.Response(
                200,
                json={"models": [{"name": "cfg-model:latest"}]},
            )
        if request.url.path.endswith("/api/generate"):
            captured["payload"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200, json={"response": '{"ok": true}'})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = OllamaClient(
        base_url="http://ollama.test",
        model="cfg-model:latest",
        timeout_sec=90.0,
        temperature=0.55,
        transport=httpx.MockTransport(handler),
    )
    text = client.generate(system="sys", prompt="prompt")
    assert '"ok"' in text
    assert captured["payload"]["model"] == "cfg-model:latest"
    assert captured["payload"]["options"]["temperature"] == 0.55
