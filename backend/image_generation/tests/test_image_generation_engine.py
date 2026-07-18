"""Unit / smoke tests for Image Generation Engine (Phase 5.1)."""

from __future__ import annotations

from image_generation.backend_registry import BackendRegistry
from image_generation.backend_router import BackendRouter
from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import ValidationError
from image_generation.generation_queue import GenerationQueue
from image_generation.image_generation_service import (
    ImageGenerationService,
    build_default_service,
)
from image_generation.models import (
    GenerationJob,
    GenerationRequest,
    GenerationStatus,
    OutputFormat,
)
from image_generation.null_backend import NullBackend
from image_generation.progress_tracker import ProgressTracker
from image_generation.validators import GenerationRequestValidator


def _ok(label: str) -> None:
    print(f"{label}: OK")


def test_request_creation() -> GenerationRequest:
    req = GenerationRequest(
        prompt="educational illustration of Earth",
        style_id="blueprint",
        width=512,
        height=512,
        aspect_ratio="1:1",
        output_format=OutputFormat.PNG,
    )
    assert req.request_id is not None
    assert req.prompt
    _ok("Request")
    return req


def test_validation(config: ImageGenerationConfig) -> None:
    validator = GenerationRequestValidator(config)
    good = GenerationRequest(
        prompt="Earth",
        style_id="flat",
        width=512,
        height=512,
        aspect_ratio="1:1",
    )
    validator.validate(good)

    bad = GenerationRequest(
        prompt="",
        style_id="not-a-style",
        width=13,
        height=13,
        aspect_ratio="99:99",
    )
    try:
        validator.validate(bad)
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    _ok("Validation")


def test_queue(config: ImageGenerationConfig) -> None:
    queue = GenerationQueue(config)
    job = GenerationJob(
        request=GenerationRequest(prompt="Moon", style_id="flat"),
        priority=5,
    )
    queue.enqueue(job)
    assert queue.size() == 1
    got = queue.dequeue()
    assert got is not None and got.job_id == job.job_id
    assert queue.size() == 0
    _ok("Queue")


def test_registry_and_null(config: ImageGenerationConfig) -> NullBackend:
    registry = BackendRegistry()
    backend = NullBackend(config)
    registry.register(backend, set_as_default=True)
    backend.initialize()
    assert registry.get_default().backend_name() == "null"
    assert len(registry.list_backends()) == 1
    health = registry.health_check()
    assert health["null"]["ready"] is True
    _ok("Backend Registry")
    return backend


def test_router(config: ImageGenerationConfig, backend: NullBackend) -> None:
    registry = BackendRegistry()
    registry.register(backend, set_as_default=True)
    router = BackendRouter(registry)
    req = GenerationRequest(prompt="Sun", style_id="cartoon")
    chosen = router.choose(req)
    assert chosen.backend_name() == "null"
    _ok("Router")


def test_null_backend(backend: NullBackend) -> None:
    req = GenerationRequest(prompt="Architecture stub test", style_id="minimal_vector")
    result = backend.generate(req)
    assert result.success is True
    assert result.message == "Architecture stub"
    assert result.output_path is None
    _ok("Null Backend")


def test_progress() -> None:
    tracker = ProgressTracker()
    from uuid import uuid4

    job_id = uuid4()
    tracker.start(job_id)
    tracker.update(job_id, GenerationStatus.GENERATING, message="working")
    snap = tracker.mark_completed(job_id, message="done")
    assert snap.status == GenerationStatus.COMPLETED
    assert snap.percent == 100.0
    _ok("Progress")


def test_health(service: ImageGenerationService) -> None:
    health = service.health()
    assert health.engine_ready is True
    assert health.engine_version == service.config.engine_version
    assert any(b.backend_id == "null" for b in health.registered_backends)
    _ok("Health")
    print(f"Engine version: {health.engine_version}")
    print(f"Registered backends: {[b.backend_id for b in health.registered_backends]}")
    print(f"Queue size: {health.queue_size}")
    print(f"Pending jobs: {health.pending_jobs}")
    print(f"Completed jobs: {health.completed_jobs}")


def test_service_end_to_end(service: ImageGenerationService) -> None:
    response = service.generate(
        GenerationRequest(
            prompt="educational illustration of Earth, front view",
            style_id="blueprint",
            width=512,
            height=512,
            aspect_ratio="1:1",
        )
    )
    assert response.status == GenerationStatus.COMPLETED
    assert response.backend_id == "null"
    assert response.message == "Architecture stub"
    assert response.output_path is None
    _ok("Service")


def main() -> None:
    print("=" * 48)
    print("ExplainX Phase 5.1 — Image Generation Engine")
    print("=" * 48)

    config = ImageGenerationConfig.from_defaults()
    test_request_creation()
    test_validation(config)
    test_queue(config)
    backend = test_registry_and_null(config)
    test_router(config, backend)
    test_null_backend(backend)
    test_progress()

    service = build_default_service(config)
    try:
        test_service_end_to_end(service)
        test_health(service)
    finally:
        service.stop()

    print("-" * 48)
    print("Backend: NullBackend")
    print("Queue: OK")
    print("Router: OK")
    print("Request: OK")
    print("Progress: OK")
    print("Health: OK")
    print("Image Generation Engine: READY")
    print("=" * 48)


if __name__ == "__main__":
    main()
