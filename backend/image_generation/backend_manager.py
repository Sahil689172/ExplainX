"""Backend manager — initialize / shutdown lifecycle for registered backends."""

from __future__ import annotations

from image_generation.backend_registry import BackendRegistry
from image_generation.interfaces import ImageBackend
from image_generation.logger import GenerationJobLogger


class BackendManager:
    """Owns backend lifecycle on top of the registry."""

    def __init__(
        self,
        registry: BackendRegistry,
        *,
        logger: GenerationJobLogger | None = None,
    ) -> None:
        self._registry = registry
        self._logger = logger or GenerationJobLogger()
        self._initialized = False

    @property
    def registry(self) -> BackendRegistry:
        return self._registry

    def initialize_all(self) -> None:
        for info in self._registry.list_backends():
            backend = self._registry.get(info.backend_id)
            backend.initialize()
            self._logger.info(
                "BACKEND_INIT",
                backend=backend.backend_name(),
                version=backend.version(),
            )
        self._initialized = True

    def shutdown_all(self) -> None:
        for info in self._registry.list_backends():
            backend = self._registry.get(info.backend_id)
            backend.shutdown()
            self._logger.info("BACKEND_SHUTDOWN", backend=backend.backend_name())
        self._initialized = False

    def initialize_one(self, backend: ImageBackend) -> None:
        backend.initialize()
        self._registry.register(backend)

    @property
    def is_initialized(self) -> bool:
        return self._initialized
