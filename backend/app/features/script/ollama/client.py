"""HTTP client for local Ollama generate API."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx

from app.core.config import Settings
from app.core.errors import ExplainXError
from app.core.logging import get_logger
from app.shared.pipeline_timing import timed_step

logger = get_logger(__name__)

# Error when settings.ollama_model is not among installed Ollama tags.
MODEL_NOT_INSTALLED = "MODEL_NOT_INSTALLED"


@runtime_checkable
class OllamaClientProtocol(Protocol):
    """Port for Ollama text generation (mockable in tests)."""

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        json_format: bool = True,
    ) -> str: ...


def _print_banner(lines: list[str]) -> None:
    print("----------------------------------------", flush=True)
    for line in lines:
        print(line, flush=True)
    print("----------------------------------------", flush=True)


class OllamaClient:
    """Thin adapter around Ollama ``/api/generate`` (non-streaming)."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_sec: float = 600.0,
        temperature: float = 0.2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_sec
        self._temperature = temperature
        self._transport = transport
        self._health_checked = False

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> OllamaClient:
        # Prefer unprefixed env vars; Settings already loads .env via AliasChoices.
        base_url = os.environ.get("OLLAMA_BASE_URL") or settings.ollama_base_url
        model = os.environ.get("OLLAMA_MODEL") or settings.ollama_model
        timeout_raw = os.environ.get("OLLAMA_TIMEOUT")
        timeout_sec = (
            float(timeout_raw) if timeout_raw is not None else settings.ollama_timeout_sec
        )
        temp_raw = os.environ.get("OLLAMA_TEMPERATURE")
        temperature = (
            float(temp_raw) if temp_raw is not None else settings.ollama_temperature
        )
        return cls(
            base_url=base_url,
            model=model,
            timeout_sec=timeout_sec,
            temperature=temperature,
            transport=transport,
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout_sec(self) -> float:
        return self._timeout

    @property
    def temperature(self) -> float:
        return self._temperature

    def list_models(self) -> list[str]:
        """Return installed model names from Ollama ``/api/tags``."""
        url = f"{self._base_url}/api/tags"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.get(url)
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

        if response.status_code >= 400:
            raise ExplainXError(
                "Ollama tags request failed.",
                code="OLLAMA_UNAVAILABLE",
                status_code=503,
                details={"status_code": response.status_code, "body": response.text[:500]},
                retriable=True,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ExplainXError(
                "Ollama returned a non-JSON tags envelope.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"body": response.text[:500]},
            ) from exc

        models: list[str] = []
        for item in data.get("models") or []:
            if isinstance(item, dict):
                name = item.get("name") or item.get("model")
                if isinstance(name, str) and name.strip():
                    models.append(name.strip())
        return models

    def model_is_installed(self, installed: list[str] | None = None) -> bool:
        """Return True when the configured model appears in the installed list."""
        names = installed if installed is not None else self.list_models()
        wanted = self._model.strip()
        if wanted in names:
            return True
        # Accept tag-equivalent forms: "name" ↔ "name:latest"
        wanted_base, _, wanted_tag = wanted.partition(":")
        for name in names:
            base, _, tag = name.partition(":")
            if base != wanted_base:
                continue
            if not wanted_tag or not tag:
                if (wanted_tag or "latest") == (tag or "latest"):
                    return True
            elif tag == wanted_tag:
                return True
        return False

    def log_connection(self) -> None:
        """Print configured Ollama endpoint and model (CLI / ops visibility)."""
        _print_banner(
            [
                "[ollama]",
                f"Base URL : {self._base_url}",
                f"Model    : {self._model}",
            ]
        )

    def log_generation_params(self) -> None:
        """Print model / temperature / timeout before each generate call."""
        timeout_display = (
            int(self._timeout) if self._timeout == int(self._timeout) else self._timeout
        )
        _print_banner(
            [
                "Model:",
                self._model,
                "",
                "Temperature:",
                str(self._temperature),
                "",
                "Timeout:",
                f"{timeout_display} sec",
            ]
        )

    def ensure_ready(self) -> list[str]:
        """Verify the server is reachable and the configured model is installed.

        Returns the list of installed model names.
        """
        installed = self.list_models()
        if not self.model_is_installed(installed):
            raise ExplainXError(
                f"Configured Ollama model '{self._model}' is not installed.",
                code=MODEL_NOT_INSTALLED,
                status_code=503,
                details={
                    "base_url": self._base_url,
                    "model": self._model,
                    "installed_models": installed,
                },
                retriable=False,
            )
        self._health_checked = True
        logger.info(
            "Ollama health check passed",
            extra={
                "event": "ollama_health_ok",
                "component": "ollama_client",
                "model": self._model,
                "installed_count": len(installed),
            },
        )
        return installed

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        json_format: bool = True,
    ) -> str:
        """Call Ollama and return the raw ``response`` text.

        ``json_format=True`` sets Ollama ``format: json`` (structured stages).
        ``json_format=False`` requests plain text (continuous narration).
        """
        with timed_step("Ollama"):
            return self._generate_impl(
                system=system, prompt=prompt, json_format=json_format
            )

    def _generate_impl(
        self,
        *,
        system: str,
        prompt: str,
        json_format: bool = True,
    ) -> str:
        if not self._health_checked:
            self.ensure_ready()

        self.log_generation_params()

        # TEMP DEBUG: full rendered prompt exactly as sent to Ollama (no truncation).
        print("================ PROMPT START ================", flush=True)
        print(self._model, flush=True)
        print("", flush=True)
        print("System:", flush=True)
        print(system, flush=True)
        print("", flush=True)
        print("Prompt:", flush=True)
        print(prompt, flush=True)
        print("================ PROMPT END ==================", flush=True)

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": self._temperature,
            },
        }
        if json_format:
            payload["format"] = "json"
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

        # TEMP DEBUG: raw Ollama response body field (no truncation).
        print("================ RESPONSE START ================", flush=True)
        print(text, flush=True)
        print("================ RESPONSE END ==================", flush=True)

        logger.info(
            "Ollama generate completed",
            extra={
                "event": "ollama_generate",
                "component": "ollama_client",
                "model": self._model,
                "temperature": self._temperature,
                "timeout_sec": self._timeout,
                "eval_count": data.get("eval_count"),
            },
        )
        return text
