"""OpenVINOBackend — ImageBackend adapter; delegates lifecycle to ModelManager."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from uuid import uuid4

from image_generation.config import ImageGenerationConfig
from image_generation.logger import GenerationJobLogger
from image_generation.models import BackendGenerateResult, GenerationRequest
from image_generation.openvino.model_manager import ModelManager


class OpenVINOBackend:
    """Phase 5.2 local backend for official OpenVINO SD 1.5 FP16.

    Engine code only sees ``ImageBackend`` — never model-repo types.
    Model: ``OpenVINO/stable-diffusion-v1-5-fp16-ov`` (via config + ModelManager).
    """

    def __init__(
        self,
        config: ImageGenerationConfig,
        *,
        model_manager: ModelManager | None = None,
        logger: GenerationJobLogger | None = None,
        force_stub: bool = False,
    ) -> None:
        self._config = config
        self._models = model_manager or ModelManager(config)
        self._logger = logger or GenerationJobLogger()
        self._force_stub = force_stub
        self._ready = False
        self._cancelled: set[str] = set()

    def backend_name(self) -> str:
        return "openvino"

    def version(self) -> str:
        return self._config.openvino_backend_version

    def initialize(self) -> None:
        self._config.output_dir().mkdir(parents=True, exist_ok=True)
        self._config.cache_dir().mkdir(parents=True, exist_ok=True)
        status = self._models.load(force_stub=self._force_stub)
        self._ready = status.pipeline_ready
        self._logger.info(
            "OPENVINO_INIT",
            repo=status.model_repo,
            device=status.device,
            kind=status.pipeline_kind,
            path=status.model_path,
            ov=status.openvino_version,
            downloaded=status.downloaded,
        )

    def generate(self, request: GenerationRequest) -> BackendGenerateResult:
        if not self._ready:
            return BackendGenerateResult(
                success=False,
                message="OpenVINOBackend not initialized",
                error="BackendNotReady",
            )

        job_hint = str(request.request_id)
        if job_hint in self._cancelled:
            self._cancelled.discard(job_hint)
            return BackendGenerateResult(
                success=False,
                message="Cancelled",
                error="cancelled",
            )

        width = self._config.openvino_width
        height = self._config.openvino_height
        if request.width != width or request.height != height:
            self._logger.info(
                "OPENVINO_SIZE_OVERRIDE",
                requested=f"{request.width}x{request.height}",
                using=f"{width}x{height}",
            )

        try:
            self._models.clear_cancel()
            seed = request.seed if request.seed is not None else self._config.openvino_seed
            png_bytes = self._models.generate_png_bytes(request.prompt, seed=seed)
            out_path = self._write_png(png_bytes, request)
            status = self._models.status()
            return BackendGenerateResult(
                success=True,
                message="Image generated",
                output_path=str(out_path),
                metadata={
                    "backend": self.backend_name(),
                    "model_repo": self._config.openvino_model_repo_id,
                    "device": status.device,
                    "pipeline_kind": status.pipeline_kind,
                    "width": width,
                    "height": height,
                    "steps": self._config.openvino_inference_steps,
                    "guidance_scale": self._config.openvino_guidance_scale,
                    "seed": seed,
                    "style_id": request.style_id,
                },
            )
        except Exception as exc:  # noqa: BLE001 — backend boundary
            self._logger.error("OPENVINO_GENERATE_FAIL", error=str(exc))
            return BackendGenerateResult(
                success=False,
                message="Generation failed",
                error=str(exc),
            )

    def cancel(self, job_id: str) -> bool:
        self._cancelled.add(str(job_id))
        self._models.request_cancel()
        return True

    def shutdown(self) -> None:
        self._models.unload()
        self._ready = False
        self._cancelled.clear()
        self._logger.info("OPENVINO_SHUTDOWN")

    def health(self) -> dict[str, object]:
        status = self._models.status()
        return {
            "backend_id": self.backend_name(),
            "ready": self._ready and status.pipeline_ready,
            "backend_ready": self._ready,
            "model_loaded": status.model_loaded,
            "pipeline_ready": status.pipeline_ready,
            "device": status.device,
            "current_device": status.device,
            "memory_usage_mb": status.memory_usage_mb,
            "openvino_version": status.openvino_version,
            "pipeline_kind": status.pipeline_kind,
            "model_path": status.model_path,
            "model_repo": status.model_repo,
            "model_downloaded": status.downloaded,
            "warmup_done": status.warmup_done,
            "inference": status.pipeline_kind not in (None, "stub"),
            "version": self.version(),
            "message": status.message,
        }

    def supported_styles(self) -> Sequence[str]:
        return list(self._config.supported_styles)

    def supported_sizes(self) -> Sequence[tuple[int, int]]:
        return [(self._config.openvino_width, self._config.openvino_height)]

    def _write_png(self, data: bytes, request: GenerationRequest) -> Path:
        out_dir = self._config.output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = (request.asset_semantic_name or "asset").strip().replace(" ", "_")
        stem = "".join(c for c in stem if c.isalnum() or c in ("_", "-")) or "asset"
        name = f"{stem}_{request.request_id.hex[:8]}_{uuid4().hex[:6]}.png"
        path = out_dir / name
        path.write_bytes(data)
        return path.resolve()
