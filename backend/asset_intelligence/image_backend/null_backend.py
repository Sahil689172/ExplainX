"""Null ImageBackend — architecture stub. No models, no inference."""

from __future__ import annotations

from asset_intelligence.schemas.prompt import (
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
)


class NullImageBackend:
    """Placeholder backend satisfying ``ImageBackend`` without running models.

    Future implementations (OpenVINO, Diffusers, ONNX, ComfyUI, Flux, SDXL)
    replace this class while keeping the same initialize/generate/health/shutdown
    contract.
    """

    backend_id: str = "null"

    def __init__(self) -> None:
        self._ready = False

    def initialize(self) -> None:
        self._ready = True

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            request_id=request.request_id,
            status=GenerationStatus.FAILED,
            error=(
                "NullImageBackend: image generation is not implemented in Phase 4.7 "
                "(architecture only)."
            ),
            backend_id=self.backend_id,
        )

    def health(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_id,
            "ready": self._ready,
            "inference": False,
            "phase": "4.7",
            "message": "Architecture stub — no model loaded",
        }

    def shutdown(self) -> None:
        self._ready = False
