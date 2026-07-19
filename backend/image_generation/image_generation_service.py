"""ImageGenerationService — permanent orchestration layer.

Knows nothing about Stable Diffusion / Flux / OpenVINO model types —
only ``ImageBackend`` (+ optional ``OutputPipelineProtocol`` via DI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from image_generation.backend_manager import BackendManager
from image_generation.backend_registry import BackendRegistry
from image_generation.backend_router import BackendRouter
from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import (
    GenerationFailedError,
    ImageGenerationError,
    ValidationError,
)
from image_generation.generation_queue import GenerationQueue
from image_generation.health import EngineHealth
from image_generation.interfaces import OutputPipelineProtocol
from image_generation.logger import GenerationJobLogger
from image_generation.models import (
    GenerationJob,
    GenerationProgress,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    HealthStatus,
)
from image_generation.null_backend import NullBackend
from image_generation.progress_tracker import ProgressTracker
from image_generation.validators import GenerationRequestValidator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ImageGenerationService:
    """Accept → Validate → Create Job → Select Backend → Execute → Respond."""

    def __init__(
        self,
        *,
        config: ImageGenerationConfig | None = None,
        registry: BackendRegistry | None = None,
        router: BackendRouter | None = None,
        queue: GenerationQueue | None = None,
        progress: ProgressTracker | None = None,
        validator: GenerationRequestValidator | None = None,
        logger: GenerationJobLogger | None = None,
        manager: BackendManager | None = None,
        output_pipeline: OutputPipelineProtocol | None = None,
        auto_register_null: bool = True,
    ) -> None:
        self.config = config or ImageGenerationConfig.from_defaults()
        self.registry = registry or BackendRegistry()
        self.router = router or BackendRouter(self.registry)
        self.queue = queue or GenerationQueue(self.config)
        self.progress = progress or ProgressTracker()
        self.validator = validator or GenerationRequestValidator(self.config)
        self.logger = logger or GenerationJobLogger()
        self.manager = manager or BackendManager(self.registry, logger=self.logger)
        self.output_pipeline = output_pipeline
        self.health_svc = EngineHealth(
            config=self.config,
            registry=self.registry,
            queue=self.queue,
            engine_ready=False,
        )

        if auto_register_null and "null" not in self.registry:
            self.registry.register(
                NullBackend(self.config),
                set_as_default=True,
            )

    def start(self) -> None:
        """Initialize registered backends and mark engine ready."""
        self.manager.initialize_all()
        self.health_svc.set_ready(True)
        self.logger.info(
            "ENGINE_START",
            version=self.config.engine_version,
            default_backend=self.registry.default_backend_id,
        )

    def stop(self) -> None:
        self.manager.shutdown_all()
        self.health_svc.set_ready(False)
        self.logger.info("ENGINE_STOP", version=self.config.engine_version)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Synchronous orchestration for one request."""
        job = GenerationJob(
            request=request,
            priority=request.priority,
            max_attempts=max(1, self.config.retry_count),
        )
        self.progress.start(job.job_id)
        self.queue.enqueue(job)

        dequeued = self.queue.dequeue()
        if dequeued is None or dequeued.job_id != job.job_id:
            return self._fail_response(
                job,
                error="Failed to dequeue job",
            )

        try:
            return self._execute_job(job)
        except ValidationError as exc:
            return self._fail_response(job, error=str(exc))
        except ImageGenerationError as exc:
            return self._fail_response(job, error=str(exc))
        except Exception as exc:  # noqa: BLE001 — engine boundary
            self.logger.job_failed(job, str(exc))
            return self._fail_response(job, error=f"Unexpected error: {exc}")

    def health(self) -> HealthStatus:
        snap = self.health_svc.snapshot()
        for info in snap.registered_backends:
            if info.is_default and info.metadata.entries.get("health"):
                snap.metadata.set(
                    "default_backend_health", info.metadata.entries["health"]
                )
                break
        return snap

    def get_progress(self, job_id: UUID) -> GenerationProgress | None:
        return self.progress.get(job_id)

    def cancel(self, job_id: UUID) -> GenerationJob:
        job = self.queue.cancel(job_id)
        if job.backend_id and job.backend_id in self.registry:
            self.registry.get(job.backend_id).cancel(str(job_id))
        self.progress.update(
            job_id,
            GenerationStatus.CANCELLED,
            message="Cancelled",
            backend_id=job.backend_id,
        )
        return job

    def _execute_job(self, job: GenerationJob) -> GenerationResponse:
        job.started_at = _utc_now()
        job.updated_at = job.started_at
        self.logger.job_started(job)

        self._set_status(job, GenerationStatus.VALIDATING, "Validating request")
        self.validator.validate(job.request)

        self._set_status(
            job, GenerationStatus.SELECTING_BACKEND, "Selecting backend"
        )
        backend_id = self.router.resolve_backend_id(job.request)
        backend = self.router.choose(job.request)
        job.backend_id = backend_id
        job.updated_at = _utc_now()

        self._set_status(
            job,
            GenerationStatus.GENERATING,
            f"Generating via {backend.backend_name()}",
            backend_id=backend_id,
        )
        job.attempts += 1
        result = backend.generate(job.request)

        if not result.success:
            raise GenerationFailedError(result.error or result.message)

        self._set_status(
            job,
            GenerationStatus.POST_PROCESSING,
            "Post processing",
            backend_id=backend_id,
        )
        job.result_message = result.message
        job.output_path = result.output_path
        job.metadata.set("backend_result", result.metadata)

        if (
            self.output_pipeline is not None
            and result.output_path
            and Path(result.output_path).is_file()
        ):
            final_path = self.output_pipeline.process(
                raw_png=result.output_path,
                request=job.request,
                job=job,
            )
            job.output_path = final_path

        job.finished_at = _utc_now()
        job.status = GenerationStatus.COMPLETED
        job.updated_at = job.finished_at
        progress = self.progress.mark_completed(
            job.job_id,
            backend_id=backend_id,
            message=result.message,
        )
        self.logger.job_finished(job)

        return GenerationResponse(
            job_id=job.job_id,
            request_id=job.request.request_id,
            status=GenerationStatus.COMPLETED,
            backend_id=backend_id,
            message=result.message,
            output_path=job.output_path,
            duration_ms=job.duration_ms,
            progress=progress,
            metadata=job.metadata,
        )

    def _set_status(
        self,
        job: GenerationJob,
        status: GenerationStatus,
        message: str,
        *,
        backend_id: str | None = None,
    ) -> None:
        job.status = status
        job.updated_at = _utc_now()
        self.progress.update(
            job.job_id,
            status,
            message=message,
            backend_id=backend_id or job.backend_id,
        )

    def _fail_response(self, job: GenerationJob, *, error: str) -> GenerationResponse:
        job.finished_at = _utc_now()
        job.status = GenerationStatus.FAILED
        job.error = error
        job.updated_at = job.finished_at
        progress = self.progress.mark_failed(
            job.job_id, error=error, backend_id=job.backend_id
        )
        self.logger.job_failed(job, error)
        return GenerationResponse(
            job_id=job.job_id,
            request_id=job.request.request_id,
            status=GenerationStatus.FAILED,
            backend_id=job.backend_id,
            message="Generation failed",
            error=error,
            duration_ms=job.duration_ms,
            progress=progress,
            metadata=job.metadata,
        )


def build_default_service(
    config: ImageGenerationConfig | None = None,
) -> ImageGenerationService:
    """Factory: config + NullBackend registered as default."""
    cfg = config or ImageGenerationConfig.from_defaults()
    service = ImageGenerationService(config=cfg, auto_register_null=True)
    service.start()
    return service


def build_openvino_service(
    config: ImageGenerationConfig | None = None,
    *,
    force_stub: bool = False,
    with_asset_pipeline: bool = True,
) -> ImageGenerationService:
    """Factory: OpenVINOBackend as default; optional Asset Processor handoff."""
    from asset_intelligence.asset_library import AssetLibrary
    from image_generation.openvino import AssetOutputPipeline, OpenVINOBackend

    cfg = config or ImageGenerationConfig.from_defaults()
    cfg.default_backend_id = "openvino"

    registry = BackendRegistry()
    ov = OpenVINOBackend(cfg, force_stub=force_stub)
    registry.register(ov, set_as_default=True)
    registry.register(NullBackend(cfg), set_as_default=False)

    output: OutputPipelineProtocol | None = None
    library = AssetLibrary()
    if with_asset_pipeline:
        output = AssetOutputPipeline(
            asset_library=library,
            use_stub_remover=force_stub,
        )

    service = ImageGenerationService(
        config=cfg,
        registry=registry,
        output_pipeline=output,
        auto_register_null=False,
    )
    # Expose library for tests / callers without breaking engine abstraction
    service.asset_library = library  # type: ignore[attr-defined]
    service.start()
    return service
