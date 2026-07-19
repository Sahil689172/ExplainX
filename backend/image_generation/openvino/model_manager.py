"""ModelManager — owns official OpenVINO SD 1.5 FP16 lifecycle.

Backends never manage model download / load / unload directly.
Model identity comes only from ``ImageGenerationConfig``.
"""

from __future__ import annotations

import gc
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import (
    DeviceInitError,
    ModelDownloadError,
    ModelLoadError,
    ModelNotFoundError,
)

logger = logging.getLogger("image_generation.model_manager")

PipelineKind = Literal["genai", "optimum", "stub"]

_DOWNLOAD_ATTEMPTS = 5
_BACKOFF_SECONDS: tuple[int, ...] = (2, 4, 8, 16, 32)

# Required IR weights for OpenVINO/stable-diffusion-v1-5-fp16-ov
_REQUIRED_WEIGHT_FILES: tuple[str, ...] = (
    "unet/openvino_model.bin",
    "text_encoder/openvino_model.bin",
    "vae_encoder/openvino_model.bin",
    "vae_decoder/openvino_model.bin",
)

_REQUIRED_MARKERS: tuple[str, ...] = (
    "model_index.json",
    "unet/openvino_model.xml",
    "text_encoder/openvino_model.xml",
    "vae_encoder/openvino_model.xml",
    "vae_decoder/openvino_model.xml",
    *_REQUIRED_WEIGHT_FILES,
)

_COMPONENT_LABELS: dict[str, str] = {
    "unet": "UNet",
    "text_encoder": "Text Encoder",
    "vae_encoder": "VAE Encoder",
    "vae_decoder": "VAE Decoder",
    "tokenizer": "Tokenizer",
    "scheduler": "Scheduler",
    "safety_checker": "Safety Checker",
    "feature_extractor": "Feature Extractor",
}


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
            print("Model verified.", flush=True)
            logger.info("MODEL_PRESENT path=%s", path)
            return path

        if not self._config.openvino_allow_download:
            raise ModelNotFoundError(
                f"Model missing at {path}. "
                f"Enable openvino_allow_download or place "
                f"{self._config.openvino_model_repo_id} there."
            )

        # Resume: never wipe the tree — only remove corrupt/incomplete files.
        if path.is_dir() and any(path.iterdir()):
            print("Resuming previous download...", flush=True)
        self._remove_corrupt_or_incomplete_files(path)
        self._download_model_with_retries(path)
        print("Verifying model...", flush=True)
        self.verify(path)
        print("Model verified.", flush=True)
        self._downloaded_this_session = True
        return path

    def discover(self) -> Path:
        """Alias used by load path — ensure + verify."""
        return self.ensure_model()

    def verify(self, path: Path | None = None) -> None:
        """Verify required IR files exist and are non-empty."""
        root = path or self.model_dir()
        if not root.is_dir():
            raise ModelNotFoundError(f"Model directory missing: {root}")

        missing = self._missing_required_files(root)
        if missing:
            raise ModelNotFoundError(
                "Model verification failed; missing or empty: "
                + ", ".join(missing)
            )

        incompletes = list(root.rglob("*.incomplete"))
        if incompletes:
            raise ModelNotFoundError(
                f"Incomplete download fragments still present "
                f"({len(incompletes)} .incomplete file(s))"
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

    def _download_model_with_retries(self, dest: Path) -> None:
        """Download with sequential Hub transfers and exponential backoff."""
        last_error: Exception | None = None
        for attempt in range(1, _DOWNLOAD_ATTEMPTS + 1):
            try:
                if attempt > 1:
                    delay = _BACKOFF_SECONDS[attempt - 2]
                    print(f"Retry {attempt}/{_DOWNLOAD_ATTEMPTS}...", flush=True)
                    print(f"Waiting {delay}s before retry...", flush=True)
                    time.sleep(delay)
                    self._remove_corrupt_or_incomplete_files(dest)

                self._download_model(dest)
                missing = self._missing_required_files(dest)
                if missing:
                    print(
                        "Verification found missing/corrupt files: "
                        + ", ".join(missing),
                        flush=True,
                    )
                    self._delete_files(dest, missing)
                    raise OSError(f"Incomplete model after download: {missing}")

                return
            except ModelDownloadError:
                raise
            except Exception as exc:  # noqa: BLE001 — download boundary
                last_error = exc
                logger.warning(
                    "MODEL_DOWNLOAD_ATTEMPT_FAILED attempt=%s/%s error=%s",
                    attempt,
                    _DOWNLOAD_ATTEMPTS,
                    exc,
                )
                print(f"Download error: {exc}", flush=True)

        msg = (
            "Model download failed after 5 retries.\n"
            "Please check network connection."
        )
        if last_error is not None:
            logger.error("MODEL_DOWNLOAD_GAVE_UP last_error=%s", last_error)
        raise ModelDownloadError(msg) from None

    def _download_model(self, dest: Path) -> None:
        try:
            from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
        except ImportError as exc:
            raise ModelNotFoundError(
                "huggingface_hub required. pip install huggingface-hub"
            ) from exc

        # Xet transfers have been unreliable (OSError decoding response body).
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

        cache = self._config.cache_dir()
        cache.mkdir(parents=True, exist_ok=True)
        dest.mkdir(parents=True, exist_ok=True)

        repo_id = self._config.openvino_model_repo_id
        logger.info(
            "MODEL_DOWNLOAD repo=%s local_dir=%s cache_dir=%s max_workers=1",
            repo_id,
            dest,
            cache,
        )

        # Prefer sequential per-file downloads for progress + resume reliability.
        try:
            remote_files = list_repo_files(repo_id=repo_id)
        except Exception:
            remote_files = []

        if remote_files:
            self._download_files_sequential(
                repo_id=repo_id,
                relative_paths=remote_files,
                dest=dest,
                cache_dir=cache,
                hf_hub_download=hf_hub_download,
            )
        else:
            # Fallback: single-worker snapshot with resume
            print("Downloading model snapshot (single worker)...", flush=True)
            kwargs: dict[str, Any] = {
                "repo_id": repo_id,
                "local_dir": str(dest),
                "cache_dir": str(cache),
                "max_workers": 1,
                "local_dir_use_symlinks": False,
            }
            try:
                snapshot_download(**kwargs, resume_download=True)
            except TypeError:
                # Newer huggingface_hub removed resume_download (always resumes)
                kwargs.pop("local_dir_use_symlinks", None)
                try:
                    snapshot_download(
                        repo_id=repo_id,
                        local_dir=str(dest),
                        cache_dir=str(cache),
                        max_workers=1,
                    )
                except TypeError:
                    snapshot_download(
                        repo_id=repo_id,
                        local_dir=str(dest),
                        cache_dir=str(cache),
                        max_workers=1,
                        local_dir_use_symlinks=False,
                    )

        logger.info("MODEL_DOWNLOAD_PASS_COMPLETE path=%s", dest)

    def _download_files_sequential(
        self,
        *,
        repo_id: str,
        relative_paths: list[str],
        dest: Path,
        cache_dir: Path,
        hf_hub_download: Any,
    ) -> None:
        # Missing large weights first when resuming (skip intact files).
        priority = {
            "unet/": 10,
            "text_encoder/": 20,
            "vae_encoder/": 30,
            "vae_decoder/": 40,
            "safety_checker/": 50,
        }

        def sort_key(name: str) -> tuple[int, str]:
            for prefix, order in priority.items():
                if name.startswith(prefix):
                    return (order, name)
            return (100, name)

        files = sorted(
            (f for f in relative_paths if not f.endswith("/")),
            key=sort_key,
        )

        last_label: str | None = None
        for rel in files:
            label = self._label_for_path(rel)
            if label != last_label:
                print(f"Downloading {label}...", flush=True)
                last_label = label

            target = dest / rel
            if target.is_file() and target.stat().st_size > 0:
                # Skip intact files (resume)
                continue

            self._hf_download_one(
                hf_hub_download=hf_hub_download,
                repo_id=repo_id,
                filename=rel,
                dest=dest,
                cache_dir=cache_dir,
            )

    def _hf_download_one(
        self,
        *,
        hf_hub_download: Any,
        repo_id: str,
        filename: str,
        dest: Path,
        cache_dir: Path,
    ) -> None:
        kwargs: dict[str, Any] = {
            "repo_id": repo_id,
            "filename": filename,
            "local_dir": str(dest),
            "cache_dir": str(cache_dir),
            "local_dir_use_symlinks": False,
        }
        try:
            hf_hub_download(**kwargs, force_download=False)
        except TypeError:
            kwargs.pop("local_dir_use_symlinks", None)
            hf_hub_download(**kwargs)

    @staticmethod
    def _label_for_path(rel: str) -> str:
        top = rel.split("/", 1)[0]
        return _COMPONENT_LABELS.get(top, top)

    def _missing_required_files(self, root: Path) -> list[str]:
        missing: list[str] = []
        for rel in _REQUIRED_MARKERS:
            path = root / rel
            if not path.is_file() or path.stat().st_size <= 0:
                missing.append(rel)
        return missing

    def _remove_corrupt_or_incomplete_files(self, root: Path) -> None:
        """Delete only incomplete fragments and empty/corrupt required files."""
        if not root.is_dir():
            return

        removed: list[str] = []
        for incomplete in root.rglob("*.incomplete"):
            try:
                incomplete.unlink(missing_ok=True)
                removed.append(str(incomplete.relative_to(root)))
            except OSError as exc:
                logger.warning("Could not remove %s: %s", incomplete, exc)

        for lock in root.rglob("*.lock"):
            try:
                lock.unlink(missing_ok=True)
            except OSError:
                pass

        for rel in self._missing_required_files(root):
            path = root / rel
            if path.is_file() and path.stat().st_size <= 0:
                try:
                    path.unlink(missing_ok=True)
                    removed.append(rel)
                except OSError:
                    pass

        if removed:
            print(
                "Removed corrupt/incomplete files: " + ", ".join(removed[:8]),
                flush=True,
            )

    def _delete_files(self, root: Path, relative_paths: Sequence[str]) -> None:
        for rel in relative_paths:
            path = root / rel
            if path.is_file():
                try:
                    path.unlink()
                    print(f"Deleted corrupt file: {rel}", flush=True)
                except OSError as exc:
                    logger.warning("Could not delete %s: %s", path, exc)

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
