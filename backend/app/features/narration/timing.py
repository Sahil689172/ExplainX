"""Narration pipeline stage timing (instrumentation only)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

_narration_timer: ContextVar[NarrationPipelineTimer | None] = ContextVar(
    "narration_pipeline_timer",
    default=None,
)


def get_narration_timer() -> NarrationPipelineTimer | None:
    return _narration_timer.get()


@dataclass
class NarrationPipelineTimer:
    """Wall-clock breakdown for one narration generation run."""

    prompt_build_sec: float = 0.0
    http_request_sec: float = 0.0
    first_token_sec: float = 0.0
    generation_sec: float = 0.0
    parsing_sec: float = 0.0
    validation_sec: float = 0.0
    artifact_write_sec: float = 0.0
    prompt_chars: int = 0
    response_chars: int = 0
    _started: float = field(default_factory=time.perf_counter)

    def set_prompt_size(self, *, system: str, prompt: str) -> None:
        self.prompt_chars = len(system) + len(prompt)

    def set_response_size(self, text: str) -> None:
        self.response_chars = len(text)

    def total_sec(self) -> float:
        return time.perf_counter() - self._started

    def print_report(self) -> None:
        print("[Timing]", flush=True)
        print(f"Prompt Build .......... {self.prompt_build_sec:.2f} sec", flush=True)
        print(f"HTTP Request .......... {self.http_request_sec:.2f} sec", flush=True)
        print(f"First Token ........... {self.first_token_sec:.2f} sec", flush=True)
        print(f"Generation ............ {self.generation_sec:.2f} sec", flush=True)
        print(f"Parsing ............... {self.parsing_sec:.2f} sec", flush=True)
        print(f"Validation ............ {self.validation_sec:.2f} sec", flush=True)
        print(f"Artifact Write ........ {self.artifact_write_sec:.2f} sec", flush=True)
        print(f"TOTAL ................. {self.total_sec():.2f} sec", flush=True)
        print(f"Prompt size ........... {self.prompt_chars} chars", flush=True)
        print(f"Response size ......... {self.response_chars} chars", flush=True)


@contextmanager
def narration_timing_scope() -> Iterator[NarrationPipelineTimer]:
    """Activate narration stage timing for the current generation run."""
    timer = NarrationPipelineTimer()
    token = _narration_timer.set(timer)
    try:
        yield timer
    finally:
        timer.print_report()
        _narration_timer.reset(token)


@contextmanager
def time_stage(setter: str, *, accumulate: bool = False) -> Iterator[list[float]]:
    """Time a block and store elapsed seconds on ``timer.<setter>``."""
    timer = get_narration_timer()
    start = time.perf_counter()
    holder: list[float] = []
    try:
        yield holder
    finally:
        elapsed = time.perf_counter() - start
        if holder:
            elapsed = holder[0]
        if timer is not None:
            if accumulate:
                current = getattr(timer, setter)
                setattr(timer, setter, current + elapsed)
            else:
                setattr(timer, setter, elapsed)
