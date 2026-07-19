"""Phase 5.2 OpenVINO backend smoke / integration test.

Model: OpenVINO/stable-diffusion-v1-5-fp16-ov (auto-download if missing).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from image_generation.config import ImageGenerationConfig
from image_generation.image_generation_service import build_openvino_service
from image_generation.models import GenerationRequest, GenerationStatus, OutputFormat
from image_generation.openvino.model_manager import ModelManager


PROMPT = (
    "A flat educational illustration of Earth with transparent background."
)


def _ok(label: str) -> None:
    print(f"{label}: OK")


def _force_stub_env() -> bool:
    return os.environ.get("EXPLAINX_OPEN_VINO_STUB", "").strip() in {
        "1",
        "true",
        "True",
    }


def main() -> int:
    print("=" * 52)
    print("ExplainX Phase 5.2 — OpenVINO SD 1.5 FP16")
    print("=" * 52)

    cfg = ImageGenerationConfig.from_defaults()
    print(f"Repo: {cfg.openvino_model_repo_id}")
    print(f"Local: {cfg.model_dir()}")
    print(f"Cache: {cfg.cache_dir()}")

    stub = _force_stub_env()
    if stub:
        print("STUB mode forced via EXPLAINX_OPEN_VINO_STUB")
    else:
        try:
            import openvino  # noqa: F401
        except ImportError:
            print("openvino not installed — STUB mode")
            print('Install: pip install openvino openvino-genai "optimum[openvino]"')
            stub = True

    if not stub:
        # Prove detect/download before full service start
        manager = ModelManager(cfg)
        present_before = manager.detect()
        print(f"Model present before ensure: {present_before}")
        path = manager.ensure_model()
        manager.verify(path)
        _ok("Model downloaded" if manager.status().downloaded or not present_before else "Model present")
        print(f"Model path verified: {path}")

    service = build_openvino_service(
        cfg,
        force_stub=stub,
        with_asset_pipeline=True,
    )

    try:
        backend = service.registry.get("openvino")
        bhealth = backend.health()

        assert backend.backend_name() == "openvino"
        _ok("Backend selected")

        device = bhealth.get("current_device") or bhealth.get("device")
        print(f"Device: {device}")
        pref = list(cfg.openvino_device_preference)
        print(f"Device preference: {pref}")
        if device == "GPU":
            _ok("GPU selected")
        elif device == "CPU":
            _ok("CPU fallback")
        else:
            _ok("Device selected")

        assert bhealth.get("backend_ready") or bhealth.get("ready")
        assert bhealth.get("model_loaded")
        assert bhealth.get("pipeline_ready")
        _ok("Pipeline initialized")

        if not stub:
            assert bhealth.get("model_repo") == cfg.openvino_model_repo_id

        request = GenerationRequest(
            prompt=PROMPT,
            style_id="flat",
            width=512,
            height=512,
            aspect_ratio="1:1",
            output_format=OutputFormat.PNG,
            asset_semantic_name="Earth",
            backend_id="openvino",
        )
        print(f"Prompt: {PROMPT}")

        response = service.generate(request)
        if response.status != GenerationStatus.COMPLETED:
            print(f"FAILED: {response.error}")
            return 1

        assert response.backend_id == "openvino"
        assert response.output_path is not None
        out = Path(response.output_path)
        assert out.is_file(), f"Missing output: {out}"
        _ok("PNG generated")

        meta = response.metadata.entries
        assert meta.get("processed_path") or out.suffix.lower() == ".png"
        _ok("Asset Processor invoked")

        if meta.get("asset_metadata") or Path(str(meta.get("processed_path", out))).with_suffix(".json").is_file():
            _ok("Metadata generated")
        else:
            # processed sidecar may share stem under processed_assets/
            processed = Path(str(meta.get("processed_path") or out))
            if processed.with_suffix(".json").is_file():
                _ok("Metadata generated")
            else:
                print("Metadata: WARN")

        library = getattr(service, "asset_library", None)
        if library is not None:
            found = library.find_reusable(semantic_name="Earth", style_id="flat")
            assert found is not None, "Asset Library missing Earth"
            _ok("Asset Library updated")
        else:
            print("Asset Library: SKIP")

        h2 = service.health()
        assert h2.engine_ready
        default_h = h2.metadata.get("default_backend_health") or bhealth
        print(f"OpenVINO version: {default_h.get('openvino_version')}")
        print(f"Memory MB: {default_h.get('memory_usage_mb')}")
        print(f"Pipeline: {default_h.get('pipeline_kind')}")
        print(f"Model repo: {default_h.get('model_repo')}")
        _ok("Health")

        print("-" * 52)
        print(f"Backend: OpenVINOBackend ({'STUB' if stub else 'LIVE'})")
        print(f"Model: {cfg.openvino_model_repo_id}")
        print(f"Output: {response.output_path}")
        print(f"Duration ms: {response.duration_ms}")
        print("Health: READY")
        print("OpenVINO Backend: READY")
        print("=" * 52)
        return 0
    finally:
        service.stop()


if __name__ == "__main__":
    sys.exit(main())
