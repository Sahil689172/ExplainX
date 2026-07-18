"""Backend router — selects which ImageBackend handles a request."""

from __future__ import annotations

from image_generation.backend_registry import BackendRegistry
from image_generation.exceptions import BackendNotFoundError, BackendNotReadyError
from image_generation.interfaces import ImageBackend
from image_generation.models import GenerationRequest


class BackendRouter:
    """Routes generation requests to a registered backend.

    Phase 5.1: everything routes to NullBackend (default) unless
    ``request.backend_id`` explicitly names another registered backend.
    """

    def __init__(self, registry: BackendRegistry) -> None:
        self._registry = registry

    def choose(self, request: GenerationRequest) -> ImageBackend:
        backend_id = request.backend_id
        if backend_id:
            backend = self._registry.get(backend_id)
        else:
            backend = self._registry.get_default()

        health = backend.health()
        if not health.get("ready", False):
            raise BackendNotReadyError(
                f"Backend {backend.backend_name()!r} is not ready"
            )
        return backend

    def resolve_backend_id(self, request: GenerationRequest) -> str:
        if request.backend_id:
            if request.backend_id not in self._registry:
                raise BackendNotFoundError(
                    f"Backend not registered: {request.backend_id!r}"
                )
            return request.backend_id
        default_id = self._registry.default_backend_id
        if default_id is None:
            raise BackendNotFoundError("No default backend registered")
        return default_id
