"""Protocols for Image Generation Engine backends and collaborators."""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from image_generation.models import (
    BackendGenerateResult,
    GenerationRequest,
)


@runtime_checkable
class ImageBackend(Protocol):
    """Contract every future image backend must implement.

    Phase 5.1 ships only ``NullBackend``. Future: OpenVINO, Diffusers,
    ONNX, ComfyUI, Flux, SDXL — no model imports in this package.
    """

    def backend_name(self) -> str:
        """Stable backend identifier (e.g. ``null``, ``openvino``)."""
        ...

    def version(self) -> str:
        """Backend adapter version string."""
        ...

    def initialize(self) -> None:
        """Allocate resources / load config. Idempotent. No model downloads."""
        ...

    def generate(self, request: GenerationRequest) -> BackendGenerateResult:
        """Execute generation for one request."""
        ...

    def cancel(self, job_id: str) -> bool:
        """Attempt to cancel in-flight work. Return True if acknowledged."""
        ...

    def shutdown(self) -> None:
        """Release resources. Safe to call multiple times."""
        ...

    def health(self) -> dict[str, object]:
        """Backend health: ready, errors, device hints, etc."""
        ...

    def supported_styles(self) -> Sequence[str]:
        """Style IDs this backend can honor."""
        ...

    def supported_sizes(self) -> Sequence[tuple[int, int]]:
        """(width, height) pairs this backend accepts."""
        ...
