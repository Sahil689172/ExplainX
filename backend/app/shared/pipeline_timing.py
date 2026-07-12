"""Pipeline performance timing — logging only, no business logic."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger("app.pipeline.timing")

_timer_var: ContextVar["PipelineTimer | None"] = ContextVar(
    "pipeline_timer", default=None
)


def _format_seconds(elapsed: float) -> str:
    return f"{elapsed:.1f} sec"


@dataclass
class PipelineTimer:
    """Accumulate wall-clock steps for one script-generation run."""

    steps: list[tuple[str, float]] = field(default_factory=list)
    _started: float = field(default_factory=time.perf_counter)

    def record(self, label: str, elapsed: float) -> None:
        self.steps.append((label, elapsed))
        line = f"[{label}] {_format_seconds(elapsed)}"
        # Always print so benchmarks show in consoles even when logging is reconfigured.
        print(line, flush=True)
        logger.info(
            line,
            extra={
                "event": "pipeline_step_timing",
                "component": "pipeline_timing",
                "stage": label,
                "duration_ms": round(elapsed * 1000.0, 1),
            },
        )

    def elapsed_total(self) -> float:
        return time.perf_counter() - self._started

    def log_total(self) -> None:
        total = self.elapsed_total()
        line = f"TOTAL: {_format_seconds(total)}"
        print(line, flush=True)
        logger.info(
            line,
            extra={
                "event": "pipeline_total_timing",
                "component": "pipeline_timing",
                "stage": "TOTAL",
                "duration_ms": round(total * 1000.0, 1),
                "step_count": len(self.steps),
            },
        )


@contextmanager
def pipeline_timing_scope(*, project_id: str | None = None) -> Iterator[PipelineTimer]:
    """Start a timing scope for one end-to-end generate_script run."""
    timer = PipelineTimer()
    token = _timer_var.set(timer)
    logger.info(
        "Pipeline timing started",
        extra={
            "event": "pipeline_timing_started",
            "component": "pipeline_timing",
            "project_id": project_id,
        },
    )
    try:
        yield timer
    finally:
        timer.log_total()
        _timer_var.reset(token)


@contextmanager
def timed_step(label: str) -> Iterator[None]:
    """Time a major pipeline step and emit ``[Label] X.X sec``."""
    start = time.perf_counter()
    logger.debug(
        "[%s] start",
        label,
        extra={
            "event": "pipeline_step_start",
            "component": "pipeline_timing",
            "stage": label,
        },
    )
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        timer = _timer_var.get()
        if timer is not None:
            timer.record(label, elapsed)
        else:
            line = f"[{label}] {_format_seconds(elapsed)}"
            print(line, flush=True)
            logger.info(
                line,
                extra={
                    "event": "pipeline_step_timing",
                    "component": "pipeline_timing",
                    "stage": label,
                    "duration_ms": round(elapsed * 1000.0, 1),
                },
            )
