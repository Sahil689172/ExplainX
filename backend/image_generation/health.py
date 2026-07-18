"""Engine health aggregation."""

from __future__ import annotations

from image_generation.backend_registry import BackendRegistry
from image_generation.config import ImageGenerationConfig
from image_generation.generation_queue import GenerationQueue
from image_generation.models import HealthStatus


class EngineHealth:
    """Builds HealthStatus from registry + queue + config."""

    def __init__(
        self,
        *,
        config: ImageGenerationConfig,
        registry: BackendRegistry,
        queue: GenerationQueue,
        engine_ready: bool = False,
    ) -> None:
        self._config = config
        self._registry = registry
        self._queue = queue
        self._engine_ready = engine_ready

    def set_ready(self, ready: bool) -> None:
        self._engine_ready = ready

    def snapshot(self) -> HealthStatus:
        backends = self._registry.list_backends()
        ready = self._engine_ready and any(b.ready for b in backends)
        return HealthStatus(
            engine_ready=ready,
            engine_version=self._config.engine_version,
            registered_backends=backends,
            queue_size=self._queue.size(),
            pending_jobs=self._queue.pending_count(),
            completed_jobs=self._queue.completed_count(),
            failed_jobs=self._queue.failed_count(),
            default_backend_id=self._registry.default_backend_id,
            message="ready" if ready else "not ready",
        )
