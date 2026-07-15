"""Passive pipeline benchmark — wall-clock timing only (no I/O except optional JSON write)."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ordered stage keys written to benchmark.json
STAGE_ORDER: tuple[str, ...] = (
    "project_creation",
    "ingestion",
    "script_generation",
    "translation",
    "audio_generation",
    "total_pipeline",
)

# Optional stages default to 0.0 when never started/stopped.
_OPTIONAL_ZERO: frozenset[str] = frozenset({"translation", "audio_generation"})

_PRINT_LABELS: dict[str, str] = {
    "project_creation": "Project Creation",
    "ingestion": "Ingestion",
    "script_generation": "Script",
    "translation": "Translation",
    "audio_generation": "Audio",
}


class BenchmarkTimer:
    """Lightweight wall-clock timer for CLI pipeline stages.

    Passive only: ``time.perf_counter()`` + optional ``json.dump``.
    Does not call models, network, DB, or threads.
    """

    __slots__ = ("_starts", "_elapsed", "_meta")

    def __init__(self) -> None:
        self._starts: dict[str, float] = {}
        self._elapsed: dict[str, float] = {}
        self._meta: dict[str, Any] = {}

    def start(self, stage_name: str) -> None:
        """Mark the start of ``stage_name``."""
        self._starts[stage_name] = time.perf_counter()

    def stop(self, stage_name: str) -> float:
        """Mark the end of ``stage_name``; return elapsed seconds."""
        started = self._starts.pop(stage_name, None)
        if started is None:
            # Stage never started — treat as zero (e.g. skipped path).
            elapsed = 0.0
        else:
            elapsed = time.perf_counter() - started
        self._elapsed[stage_name] = elapsed
        return elapsed

    def record(self, stage_name: str, elapsed_seconds: float) -> None:
        """Store a pre-measured elapsed time (e.g. skipped stage → 0)."""
        self._elapsed[stage_name] = float(elapsed_seconds)
        self._starts.pop(stage_name, None)

    def is_running(self, stage_name: str) -> bool:
        return stage_name in self._starts

    def set_meta(self, **kwargs: Any) -> None:
        """Attach non-timing fields (language, model, voice, …)."""
        self._meta.update(kwargs)

    def elapsed(self, stage_name: str) -> float:
        """Return stored elapsed seconds for a stage (0 if missing/optional)."""
        if stage_name in self._elapsed:
            return float(self._elapsed[stage_name])
        if stage_name in _OPTIONAL_ZERO:
            return 0.0
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable benchmark payload."""
        payload: dict[str, Any] = {}
        for key in STAGE_ORDER:
            if key in self._elapsed:
                payload[key] = round(self._elapsed[key], 2)
            elif key in _OPTIONAL_ZERO:
                payload[key] = 0.0
            else:
                payload[key] = round(self._elapsed.get(key, 0.0), 2)

        # Preserve any extra measured stages (future-proof).
        for key, value in self._elapsed.items():
            if key not in payload:
                payload[key] = round(value, 2)

        payload.update(self._meta)
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return payload

    def summary(self) -> None:
        """Print the BENCHMARK banner to stdout."""
        data = self.to_dict()
        print("----------------------------------------", flush=True)
        print("BENCHMARK", flush=True)
        for key in (
            "project_creation",
            "ingestion",
            "script_generation",
            "translation",
            "audio_generation",
        ):
            label = _PRINT_LABELS[key]
            print(f"{label} : {float(data.get(key, 0.0)):.2f} sec", flush=True)
        print("----------------------------------------", flush=True)
        print(f"TOTAL : {float(data.get('total_pipeline', 0.0)):.2f} sec", flush=True)

    def save(self, path: Path | str) -> Path:
        """Write ``to_dict()`` as JSON. Only filesystem write; no network."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        out.write_text(
            json.dumps(payload, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return out
