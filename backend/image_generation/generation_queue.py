"""Lightweight in-memory generation queue (sync; async-ready API)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque
from uuid import UUID

from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import JobNotFoundError, QueueFullError
from image_generation.models import GenerationJob, GenerationStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class QueueEntry:
    job: GenerationJob
    enqueued_at: datetime = field(default_factory=_utc_now)


class GenerationQueue:
    """Priority-aware FIFO queue. Higher ``priority`` dequeues first.

    No threading required in Phase 5.1; API shaped for future async workers.
    """

    def __init__(self, config: ImageGenerationConfig) -> None:
        self._config = config
        self._pending: Deque[QueueEntry] = deque()
        self._by_id: dict[UUID, GenerationJob] = {}
        self._cancelled: set[UUID] = set()

    def enqueue(self, job: GenerationJob) -> GenerationJob:
        if len(self._pending) >= self._config.max_queue_size:
            raise QueueFullError(
                f"Queue full (max={self._config.max_queue_size})"
            )
        job.status = GenerationStatus.QUEUED
        job.updated_at = _utc_now()
        self._by_id[job.job_id] = job
        self._pending.append(QueueEntry(job=job))
        self._reorder()
        return job

    def dequeue(self) -> GenerationJob | None:
        while self._pending:
            entry = self._pending.popleft()
            job = entry.job
            if job.job_id in self._cancelled:
                job.status = GenerationStatus.CANCELLED
                job.updated_at = _utc_now()
                continue
            return job
        return None

    def cancel(self, job_id: UUID) -> GenerationJob:
        job = self._by_id.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        self._cancelled.add(job_id)
        job.status = GenerationStatus.CANCELLED
        job.updated_at = _utc_now()
        job.error = "cancelled"
        # Remove from pending if still waiting
        self._pending = deque(e for e in self._pending if e.job.job_id != job_id)
        return job

    def retry(self, job_id: UUID) -> GenerationJob:
        job = self._by_id.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        if job.attempts >= job.max_attempts:
            raise JobNotFoundError(
                f"Job {job_id} exhausted retries ({job.attempts}/{job.max_attempts})"
            )
        self._cancelled.discard(job_id)
        job.error = None
        job.result_message = None
        job.output_path = None
        job.started_at = None
        job.finished_at = None
        job.status = GenerationStatus.QUEUED
        job.updated_at = _utc_now()
        self._pending.append(QueueEntry(job=job))
        self._reorder()
        return job

    def get(self, job_id: UUID) -> GenerationJob | None:
        return self._by_id.get(job_id)

    def size(self) -> int:
        return len(self._pending)

    def pending_count(self) -> int:
        return sum(
            1
            for j in self._by_id.values()
            if j.status
            in (
                GenerationStatus.QUEUED,
                GenerationStatus.VALIDATING,
                GenerationStatus.SELECTING_BACKEND,
                GenerationStatus.GENERATING,
                GenerationStatus.POST_PROCESSING,
            )
        )

    def completed_count(self) -> int:
        return sum(
            1 for j in self._by_id.values() if j.status == GenerationStatus.COMPLETED
        )

    def failed_count(self) -> int:
        return sum(
            1 for j in self._by_id.values() if j.status == GenerationStatus.FAILED
        )

    def _reorder(self) -> None:
        ordered = sorted(
            self._pending,
            key=lambda e: (-e.job.priority, e.enqueued_at),
        )
        self._pending = deque(ordered)
