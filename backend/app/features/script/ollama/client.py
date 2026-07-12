"""HTTP client for local Ollama generate API."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx

from app.core.config import Settings
from app.core.errors import ExplainXError
from app.core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class OllamaClientProtocol(Protocol):
    """Port for Ollama text generation (mockable in tests)."""

    def generate(self, *, system: str, prompt: str) -> str: ...


class OllamaClient:
    """Thin adapter around Ollama ``/api/generate`` (non-streaming)."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_sec: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_sec
        self._transport = transport

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> OllamaClient:
        # Prefer unprefixed env vars as specified for Phase 3.5.
        base_url = os.environ.get("OLLAMA_BASE_URL") or settings.ollama_base_url
        model = os.environ.get("OLLAMA_MODEL") or settings.ollama_model
        return cls(
            base_url=base_url,
            model=model,
            timeout_sec=settings.ollama_timeout_sec,
            transport=transport,
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def generate(self, *, system: str, prompt: str) -> str:
        """Call Ollama and return the raw ``response`` text."""
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
            },
        }
        url = f"{self._base_url}/api/generate"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(url, json=payload)
        except httpx.ConnectError as exc:
            raise ExplainXError(
                "Ollama is unavailable (connection failed).",
                code="OLLAMA_UNAVAILABLE",
                status_code=503,
                details={"base_url": self._base_url, "model": self._model},
                retriable=True,
            ) from exc
        except httpx.TimeoutException as exc:
            raise ExplainXError(
                "Ollama request timed out.",
                code="OLLAMA_TIMEOUT",
                status_code=504,
                details={
                    "base_url": self._base_url,
                    "model": self._model,
                    "timeout_sec": self._timeout,
                },
                retriable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise ExplainXError(
                "Ollama request failed.",
                code="OLLAMA_UNAVAILABLE",
                status_code=503,
                details={"base_url": self._base_url, "error": str(exc)},
                retriable=True,
            ) from exc

        if response.status_code >= 500:
            raise ExplainXError(
                "Ollama server error.",
                code="OLLAMA_UNAVAILABLE",
                status_code=503,
                details={"status_code": response.status_code, "body": response.text[:500]},
                retriable=True,
            )
        if response.status_code >= 400:
            raise ExplainXError(
                "Ollama rejected the generate request.",
                code="OLLAMA_UNAVAILABLE",
                status_code=502,
                details={"status_code": response.status_code, "body": response.text[:500]},
                retriable=False,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ExplainXError(
                "Ollama returned a non-JSON envelope.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"body": response.text[:500]},
            ) from exc

        text = data.get("response")
        if text is None:
            raise ExplainXError(
                "Ollama response missing 'response' field.",
                code="OLLAMA_EMPTY_RESPONSE",
                status_code=502,
                details={"keys": sorted(data.keys())},
            )
        if not isinstance(text, str) or not text.strip():
            raise ExplainXError(
                "Ollama returned an empty response.",
                code="OLLAMA_EMPTY_RESPONSE",
                status_code=502,
                details={"model": self._model},
            )

        logger.info(
            "Ollama generate completed",
            extra={
                "event": "ollama_generate",
                "component": "ollama_client",
                "model": self._model,
                "eval_count": data.get("eval_count"),
            },
        )
        return text
