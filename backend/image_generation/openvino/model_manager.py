"""ModelManager — owns official OpenVINO SD 1.5 FP16 lifecycle.

Backends never manage model download / load / unload directly.
Model identity comes only from ``ImageGenerationConfig``.
"""

from __future__ import annotations

import gc
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import (
    DeviceInitError,
    ModelLoadError,
    ModelNotFoundError,
)

logger = logging.getLogger("image_generation.model_manager")

PipelineKind = Literal["genai", "optimum", "stub"]

# Minimum files expected for OpenVINO/stable-diffusion-v1-5-fp16-ov
_REQUIRED_MARKERS: tuple[str, ...] = (
    "model_index.json",
)


@dataclass(slots=True)
class ModelStatus:
    """Snapshot of model / device state for health reporting."""

    model_loaded: bool = False
    pipeline_ready: bool = False
    pipeline_kind: str | None = None
    device: str | None = None
    model_path: str | None = None
    model_repo: str | None = None
    openvino_version: str | None = None
    memory_usage_mb: float | None = None
    warmup_done: bool = False
    downloaded: bool = False
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelManager:
    """Detect → download if needed → verify → load once → warmup → cache → unload."""

    def __init__(self, config: ImageGenerationConfig) -> None:
        self._config = config
        self._pipeline: Any = None
        self._kind: PipelineKind | None = None
        self._device: str | None = None
        self._warmup_done = False
        self._cancel_requested = False
        self._downloaded_this_session = False

    def model_dir(self) -> Path:
        return self._config.model_dir()

    def detect(self) -> bool:
        """Return True if a complete local model tree is present."""
        try:
            self.verify(self.model_dir())
            return True
        except ModelNotFoundError:
            return False

    def ensure_model(self) -> Path:
        """Detect local model; download from Hugging Face if absent/incomplete."""
        path = self.model_dir()
        if self.detect():
            logger.info("MODEL_PRESENT path=%s", path)
            return path

        if not self._config.openvino_allow_download:
            raise ModelNotFoundError(
                f"Model missing at {path}. "
                f"Enable openvino_allow_download or place "
                f"{self._config.openvino_model_repo_id} there."
            )

        self._purge_incomplete(path)
        self._download_model(path)
        self.verify(path)
        self._downloaded_this_session = True
        return path

    def discover(self) -> Path:
        """Alias used by load path — ensure + verify."""
        return self.ensure_model()

    def verify(self, path: Path | None = None) -> None:
        """Verify OpenVINO IR layout and reject incomplete HF downloads."""
        root = path or self.model_dir()
        if not root.is_dir():
            raise ModelNotFoundError(f"Model directory missing: {root}")

        incompletes = list(root.rglob("*.incomplete"))
        if incompletes:
            raise ModelNotFoundError(
                f"Incomplete download under {root} "
                f"({len(incompletes)} .incomplete file(s))"
            )

        for marker in _REQUIRED_MARKERS:
            if not (root / marker).is_file():
                raise ModelNotFoundError(f"Missing required file: {root / marker}")

        xml_files = list(root.rglob("*.xml"))
        if not xml_files:
            raise ModelNotFoundError(
                f"No OpenVINO IR XML found under {root}"
            )

        # Prefer having unet IR for SD 1.5
        unet_xml = list((root / "unet").glob("*.xml")) if (root / "unet").is_dir() else []
        if not unet_xml:
            # Some packs nest differently — require at least one sizable xml set
            if len(xml_files) < 2:
                raise ModelNotFoundError(
                    f"Insufficient IR components under {root}"
                )

    def verify_openvino_runtime(self) -> str:
        try:
            import openvino as ov

            return str(ov.__version__)
        except ImportError as exc:
            raise ModelLoadError(
                "openvino is not installed. "
                "pip install openvino openvino-genai 'optimum[openvino]'"
            ) from exc

    def load(self, *, force_stub: bool = False) -> ModelStatus:
        if self._pipeline is not None and not force_stub:
            return self.status()

        if force_stub or os.environ.get("EXPLAINX_OPEN_VINO_STUB", "").strip() in {
            "1",
            "true",
            "True",
        }:
            return self._load_stub()

        version = self.verify_openvino_runtime()
        model_path = self.ensure_model()
        self._config.cache_dir().mkdir(parents=True, exist_ok=True)

        last_error: Exception | None = None
        for device in self._config.openvino_device_preference:
            try:
                self._pipeline, self._kind = self._create_pipeline(model_path, device)
                self._device = device
                logger.info(
                    "MODEL_LOADED repo=%s kind=%s device=%s path=%s ov=%s",
                    self._config.openvino_model_repo_id,
                    self._kind,
                    device,
                    model_path,
                    version,
                )
                if self._config.openvino_warmup_on_load:
                    self.warmup()
                return self.status()
            except Exception as exc:  # noqa: BLE001 — try next device
                last_error = exc
                logger.warning("Device %s failed: %s — trying fallback", device, exc)
                self._pipeline = None
                self._kind = None
                self._device = None

        raise DeviceInitError(
            f"Failed to load {self._config.openvino_model_repo_id} on "
            f"{self._config.openvino_device_preference}: {last_error}"
        )

    def warmup(self) -> None:
        if self._pipeline is None:
            raise ModelLoadError("Cannot warmup: pipeline not loaded")
        if self._kind == "stub":
            self._warmup_done = True
            return
        steps = max(1, min(self._config.openvino_warmup_steps, self._config.openvino_inference_steps))
        self._run_inference("warmup educational circle", seed=0, steps_override=steps)
        self._warmup_done = True
        logger.info("MODEL_WARMUP_DONE device=%s steps=%s", self._device, steps)

    def unload(self) -> None:
        self._pipeline = None
        self._kind = None
        self._device = None
        self._warmup_done = False
        gc.collect()
        logger.info("MODEL_UNLOADED")

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def clear_cancel(self) -> None:
        self._cancel_requested = False

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    def generate_png_bytes(self, prompt: str, *, seed: int | None = None) -> bytes:
        """Run one 512×512 generation; return PNG bytes."""
        if self._pipeline is None:
            raise ModelLoadError("Pipeline not loaded — call load() first")
        if self._cancel_requested:
            self._cancel_requested = False
            raise ModelLoadError("Generation cancelled")

        from io import BytesIO

        from PIL import Image

        if self._kind == "stub":
            image = Image.new("RGB", (512, 512), color=(40, 120, 200))
        else:
            image = self._run_inference(
                prompt,
                seed=seed if seed is not None else self._config.openvino_seed,
            )

        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    def status(self) -> ModelStatus:
        present = False
        try:
            present = self.detect()
        except Exception:  # noqa: BLE001
            present = False
        return ModelStatus(
            model_loaded=self._pipeline is not None,
            pipeline_ready=self._pipeline is not None,
            pipeline_kind=self._kind,
            device=self._device,
            model_path=str(self.model_dir()),
            model_repo=self._config.openvino_model_repo_id,
            openvino_version=self._safe_ov_version(),
            memory_usage_mb=self._memory_usage_mb(),
            warmup_done=self._warmup_done,
            downloaded=self._downloaded_this_session or present,
            message="ready" if self._pipeline is not None else "not loaded",
            metadata={
                "steps": self._config.openvino_inference_steps,
                "guidance_scale": self._config.openvino_guidance_scale,
                "scheduler": self._config.openvino_scheduler,
                "model_repo": self._config.openvino_model_repo_id,
                "devices_tried": list(self._config.openvino_device_preference),
            },
        )

    def _load_stub(self) -> ModelStatus:
        self._pipeline = object()
        self._kind = "stub"
        self._device = "STUB"
        self._warmup_done = True
        logger.warning("MODEL_STUB_LOADED — no OpenVINO inference")
        return self.status()

    def _create_pipeline(self, model_path: Path, device: str) -> tuple[Any, PipelineKind]:
        try:
            import openvino_genai as ov_genai

            pipe = ov_genai.Text2ImagePipeline(str(model_path), device)
            return pipe, "genai"
        except Exception as genai_exc:  # noqa: BLE001
            logger.info("GenAI unavailable (%s); trying Optimum", genai_exc)

        try:
            try:
                from optimum.intel.openvino import OVDiffusionPipeline as _Pipe
            except ImportError:
                from optimum.intel import OVStableDiffusionPipeline as _Pipe

            pipe = _Pipe.from_pretrained(
                str(model_path),
                device=device,
                safety_checker=None,
            )
            return pipe, "optimum"
        except Exception as opt_exc:  # noqa: BLE001
            raise ModelLoadError(
                f"Could not create GenAI or Optimum pipeline on {device}: {opt_exc}"
            ) from opt_exc

    def _run_inference(
        self,
        prompt: str,
        *,
        seed: int,
        steps_override: int | None = None,
    ) -> Any:
        from PIL import Image

        width = self._config.openvino_width
        height = self._config.openvino_height
        steps = steps_override if steps_override is not None else self._config.openvino_inference_steps
        guidance = self._config.openvino_guidance_scale

        if self._kind == "genai":
            tensor = self._pipeline.generate(
                prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                num_images_per_prompt=1,
                guidance_scale=guidance,
                rng_seed=seed,
            )
            return Image.fromarray(tensor.data[0])

        result = self._pipeline(
            prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=self._torch_generator(seed),
        )
        return result.images[0]

    @staticmethod
    def _torch_generator(seed: int) -> Any:
        try:
            import torch

            return torch.Generator(device="cpu").manual_seed(seed)
        except ImportError:
            return None

    def _download_model(self, dest: Path) -> None:
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise ModelNotFoundError(
                "huggingface_hub required. pip install huggingface-hub"
            ) from exc

        cache = self._config.cache_dir()
        cache.mkdir(parents=True, exist_ok=True)
        dest.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "MODEL_DOWNLOAD repo=%s local_dir=%s cache_dir=%s",
            self._config.openvino_model_repo_id,
            dest,
            cache,
        )
        snapshot_download(
            repo_id=self._config.openvino_model_repo_id,
            local_dir=str(dest),
            cache_dir=str(cache),
        )
        logger.info("MODEL_DOWNLOAD_COMPLETE path=%s", dest)

    @staticmethod
    def _purge_incomplete(path: Path) -> None:
        """Remove a broken/partial tree so download can restart cleanly."""
        if not path.exists():
            return
        if path.is_dir():
            # Only purge if incomplete markers or missing integrity
            incompletes = list(path.rglob("*.incomplete"))
            has_index = (path / "model_index.json").is_file()
            if incompletes or not has_index:
                logger.warning("Purging incomplete model tree at %s", path)
                shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def _safe_ov_version() -> str | None:
        try:
            import openvino as ov

            return str(ov.__version__)
        except ImportError:
            return None

    @staticmethod
    def _memory_usage_mb() -> float | None:
        try:
            import psutil

            return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
        except Exception:  # noqa: BLE001
            return None

    def supported_devices_attempted(self) -> Sequence[str]:
        return self._config.openvino_device_preference
