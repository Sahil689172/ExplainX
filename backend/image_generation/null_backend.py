"""NullBackend — exercises the engine without models or pixels."""

from __future__ import annotations

import time
from typing import Sequence
from uuid import UUID

from image_generation.config import ImageGenerationConfig
from image_generation.models import BackendGenerateResult, GenerationRequest


class NullBackend:
    """Architecture stub backend.

    Accepts a request, sleeps briefly, returns a successful stub response.
    Never loads models or writes image files.
    """

    def __init__(self, config: ImageGenerationConfig | None = None) -> None:
        self._config = config or ImageGenerationConfig.from_defaults()
        self._ready = False
        self._cancelled: set[str] = set()

    def backend_name(self) -> str:
        return "null"

    def version(self) -> str:
        return "1.0.0-null"

    def initialize(self) -> None:
        self._ready = True
        self._cancelled.clear()

    def generate(self, request: GenerationRequest) -> BackendGenerateResult:
        if not self._ready:
            return BackendGenerateResult(
                success=False,
                message="NullBackend not initialized",
                error="BackendNotReady",
            )

        time.sleep(self._config.null_backend_sleep_seconds)

        job_hint = str(request.request_id)
        if job_hint in self._cancelled:
            return BackendGenerateResult(
                success=False,
                message="Cancelled",
                error="cancelled",
            )

        return BackendGenerateResult(
            success=True,
            message="Architecture stub",
            output_path=None,
            metadata={
                "backend": self.backend_name(),
                "inference": False,
                "prompt_preview": request.prompt[:80],
                "style_id": request.style_id,
                "size": f"{request.width}x{request.height}",
            },
        )

    def cancel(self, job_id: str) -> bool:
        self._cancelled.add(str(job_id))
        return True

    def shutdown(self) -> None:
        self._ready = False
        self._cancelled.clear()

    def health(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_name(),
            "ready": self._ready,
            "inference": False,
            "message": "Architecture stub — no model loaded",
            "version": self.version(),
        }

    def supported_styles(self) -> Sequence[str]:
        return list(self._config.supported_styles)

    def supported_sizes(self) -> Sequence[tuple[int, int]]:
        return list(self._config.supported_resolutions)

    def mark_cancelled_job(self, job_id: UUID) -> None:
        self.cancel(str(job_id))
