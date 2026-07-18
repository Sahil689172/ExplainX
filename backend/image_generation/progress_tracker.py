"""Backend-independent progress tracking for generation jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from image_generation.models import GenerationProgress, GenerationStatus

_STATUS_PERCENT: dict[GenerationStatus, float] = {
    GenerationStatus.QUEUED: 0.0,
    GenerationStatus.VALIDATING: 10.0,
    GenerationStatus.SELECTING_BACKEND: 20.0,
    GenerationStatus.GENERATING: 50.0,
    GenerationStatus.POST_PROCESSING: 85.0,
    GenerationStatus.COMPLETED: 100.0,
    GenerationStatus.FAILED: 100.0,
    GenerationStatus.CANCELLED: 100.0,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProgressTracker:
    """Tracks Queued → … → Completed/Failed independently of backends."""

    def __init__(self) -> None:
        self._progress: dict[UUID, GenerationProgress] = {}

    def start(self, job_id: UUID) -> GenerationProgress:
        return self.update(
            job_id,
            GenerationStatus.QUEUED,
            message="Job queued",
        )

    def update(
        self,
        job_id: UUID,
        status: GenerationStatus,
        *,
        message: str = "",
        backend_id: str | None = None,
        percent: float | None = None,
    ) -> GenerationProgress:
        snap = GenerationProgress(
            job_id=job_id,
            status=status,
            percent=percent if percent is not None else _STATUS_PERCENT.get(status, 0.0),
            message=message or status.value,
            backend_id=backend_id,
            updated_at=_utc_now(),
        )
        self._progress[job_id] = snap
        return snap

    def get(self, job_id: UUID) -> GenerationProgress | None:
        return self._progress.get(job_id)

    def mark_completed(
        self, job_id: UUID, *, backend_id: str | None = None, message: str = ""
    ) -> GenerationProgress:
        return self.update(
            job_id,
            GenerationStatus.COMPLETED,
            message=message or "Completed",
            backend_id=backend_id,
        )

    def mark_failed(
        self, job_id: UUID, *, error: str, backend_id: str | None = None
    ) -> GenerationProgress:
        return self.update(
            job_id,
            GenerationStatus.FAILED,
            message=error,
            backend_id=backend_id,
        )
