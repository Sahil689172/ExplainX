"""Phase 5.4 — Smart Asset Library CLI test.

Run from backend/:

    python test_asset_library.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from image_generation.asset_manager import AssetManager
from image_generation.config import ImageGenerationConfig
from image_generation.image_generation_service import build_openvino_service


def _run_case(manager: AssetManager, prompt: str, label: str) -> None:
    print("-" * 56, flush=True)
    print(f"Case: {label}", flush=True)
    print(f"Prompt: {prompt}", flush=True)
    started = time.perf_counter()
    result = manager.resolve(prompt)
    wall_ms = (time.perf_counter() - started) * 1000.0
    print(f"Lookup Time: {result.lookup_ms:.2f} ms", flush=True)
    if result.cache_hit:
        print("Generation Time: 0.00 ms (skipped OpenVINO)", flush=True)
    else:
        print(f"Generation Time: {(result.generation_ms or 0):.2f} ms", flush=True)
    print(f"Wall Time: {wall_ms:.2f} ms", flush=True)
    print(f"Title: {result.title}", flush=True)
    if result.file_path:
        print(f"File: {result.file_path}", flush=True)
    print(f"Message: {result.message}", flush=True)


def main() -> int:
    print("=" * 56)
    print("ExplainX Phase 5.4 — Smart Asset Library")
    print("=" * 56)

    # Isolate library under a temp-like folder for repeatable CLI runs? No —
    # use the real asset_library so cache hits work across runs. Document that.
    cfg = ImageGenerationConfig.from_defaults()
    service = build_openvino_service(cfg, with_asset_pipeline=True)
    manager = AssetManager(service)

    try:
        cases = [
            ("Earth", "Generate Earth"),
            ("Earth", "Generate Earth again (expect CACHE HIT)"),
            ("Planet Earth", "Generate Planet Earth (expect reuse Earth)"),
            ("Volcano", "Generate Volcano"),
            ("Volcano", "Generate Volcano again (expect CACHE HIT)"),
        ]
        for prompt, label in cases:
            _run_case(manager, prompt, label)

        print("=" * 56)
        print("Statistics:", manager.stats)
        print(
            "Library root:",
            Path(manager.library.root),
        )
        print("=" * 56)
        return 0
    finally:
        service.stop()


if __name__ == "__main__":
    raise SystemExit(main())
