"""Image generation backend interface — architecture only, no models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asset_intelligence.schemas.prompt import GenerationRequest, GenerationResult


@runtime_checkable
class ImageBackend(Protocol):
    """Contract every future image backend must satisfy.

    Supported (future) backends: OpenVINO, Diffusers, ONNX, ComfyUI,
    Flux, SDXL, and successors. This protocol never imports model code.
    """

    backend_id: str

    def initialize(self) -> None:
        """Allocate resources / load config. Must be idempotent."""
        ...

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Produce one image for a prompt bundle. Not implemented in Phase 4.7."""
        ...

    def health(self) -> dict[str, object]:
        """Return backend health: ready, device, errors, etc."""
        ...

    def shutdown(self) -> None:
        """Release resources. Safe to call multiple times."""
        ...
