"""Batch educational prompt smoke test — reuses Phase 5.2 OpenVINO pipeline.

Run from backend/:

    python test_prompts.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from image_generation.config import ImageGenerationConfig
from image_generation.image_generation_service import build_openvino_service
from image_generation.models import GenerationRequest, GenerationStatus, OutputFormat

PROMPTS: list[str] = [
    "A flat educational illustration of the Solar System",
    "A clean vector diagram of the human heart",
    "A textbook illustration of the water cycle",
    "An infographic showing photosynthesis",
    "A minimal illustration of a volcano cross section",
    "A labeled diagram of a computer motherboard",
    "An educational illustration of DNA",
    "A flat icon style Earth globe",
]


def _semantic_name(prompt: str, index: int) -> str:
    words = re.findall(r"[A-Za-z0-9]+", prompt.lower())
    stem = "_".join(words[:6]) if words else f"prompt_{index}"
    return f"prompt_{index:02d}_{stem}"[:80]


def main() -> int:
    print("=" * 56)
    print("ExplainX — Educational Prompt Batch Test")
    print("=" * 56)

    cfg = ImageGenerationConfig.from_defaults()
    output_folder = Path(cfg.resolve_path("processed_assets"))
    output_folder.mkdir(parents=True, exist_ok=True)

    service = build_openvino_service(cfg, with_asset_pipeline=True)
    successful = 0
    failed = 0
    durations: list[float] = []

    try:
        health = service.health()
        print(f"Engine ready: {health.engine_ready}")
        print(f"Default backend: {health.default_backend_id}")
        print(f"Output folder: {output_folder}")
        print("-" * 56)

        for i, prompt in enumerate(PROMPTS, start=1):
            print(f"Generating: {prompt}", flush=True)
            started = time.perf_counter()
            request = GenerationRequest(
                prompt=prompt,
                style_id="flat",
                width=512,
                height=512,
                aspect_ratio="1:1",
                output_format=OutputFormat.PNG,
                asset_semantic_name=_semantic_name(prompt, i),
                backend_id="openvino",
            )
            try:
                response = service.generate(request)
                elapsed = time.perf_counter() - started
                durations.append(elapsed)

                if (
                    response.status != GenerationStatus.COMPLETED
                    or not response.output_path
                ):
                    failed += 1
                    print(f"✗ Failed: {response.error or response.message}", flush=True)
                    continue

                saved = Path(response.output_path)
                if not saved.is_file():
                    failed += 1
                    print(f"✗ Failed: missing file {saved}", flush=True)
                    continue

                successful += 1
                print("✓ Saved:", flush=True)
                print(str(saved.resolve()), flush=True)
                print(f"  Time: {elapsed:.2f}s", flush=True)
            except Exception as exc:  # noqa: BLE001 — batch boundary
                elapsed = time.perf_counter() - started
                durations.append(elapsed)
                failed += 1
                print(f"✗ Failed: {exc}", flush=True)

            print("-" * 56, flush=True)

    finally:
        service.stop()

    avg = sum(durations) / len(durations) if durations else 0.0
    print("Total Images:", len(PROMPTS))
    print("Successful:", successful)
    print("Failed:", failed)
    print(f"Average Generation Time: {avg:.2f}s")
    print("Output Folder:", str(output_folder.resolve()))
    print("=" * 56)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
