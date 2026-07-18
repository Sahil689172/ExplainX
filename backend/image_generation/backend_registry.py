"""Backend registry — register, lookup, default, health."""

from __future__ import annotations

from image_generation.exceptions import BackendNotFoundError
from image_generation.interfaces import ImageBackend
from image_generation.models import BackendInfo, GenerationMetadata


class BackendRegistry:
    """In-memory registry of ImageBackend implementations."""

    def __init__(self) -> None:
        self._backends: dict[str, ImageBackend] = {}
        self._default_id: str | None = None

    def register(
        self,
        backend: ImageBackend,
        *,
        set_as_default: bool = False,
    ) -> None:
        backend_id = backend.backend_name()
        self._backends[backend_id] = backend
        if set_as_default or self._default_id is None:
            self._default_id = backend_id

    def remove(self, backend_id: str) -> None:
        if backend_id not in self._backends:
            raise BackendNotFoundError(f"Backend not registered: {backend_id!r}")
        del self._backends[backend_id]
        if self._default_id == backend_id:
            self._default_id = next(iter(self._backends), None)

    def get(self, backend_id: str) -> ImageBackend:
        try:
            return self._backends[backend_id]
        except KeyError as exc:
            raise BackendNotFoundError(
                f"Backend not registered: {backend_id!r}"
            ) from exc

    def get_default(self) -> ImageBackend:
        if self._default_id is None:
            raise BackendNotFoundError("No default backend registered")
        return self.get(self._default_id)

    @property
    def default_backend_id(self) -> str | None:
        return self._default_id

    def set_default(self, backend_id: str) -> None:
        if backend_id not in self._backends:
            raise BackendNotFoundError(f"Backend not registered: {backend_id!r}")
        self._default_id = backend_id

    def list_backends(self) -> list[BackendInfo]:
        infos: list[BackendInfo] = []
        for backend_id, backend in self._backends.items():
            health = backend.health()
            infos.append(
                BackendInfo(
                    backend_id=backend_id,
                    name=backend.backend_name(),
                    version=backend.version(),
                    ready=bool(health.get("ready", False)),
                    supported_styles=list(backend.supported_styles()),
                    supported_sizes=list(backend.supported_sizes()),
                    is_default=backend_id == self._default_id,
                    metadata=GenerationMetadata(entries={"health": health}),
                )
            )
        return infos

    def health_check(self) -> dict[str, dict[str, object]]:
        return {
            backend_id: dict(backend.health())
            for backend_id, backend in self._backends.items()
        }

    def __contains__(self, backend_id: str) -> bool:
        return backend_id in self._backends

    def __len__(self) -> int:
        return len(self._backends)
