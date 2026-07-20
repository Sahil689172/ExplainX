"""DiffusersBackend — local HuggingFace ``diffusers`` inference (Task 4).

Implements the :class:`~image_generation.interfaces.ImageBackend` contract for
FLUX / SDXL-family models declared in :mod:`model_catalog`. Heavy libraries
(``torch``, ``diffusers``) are imported lazily so importing this module never
fails on machines without a GPU stack. When the dependencies or weights are
unavailable the backend reports ``health()["ready"] = False`` and the factory
falls back to another backend.
"""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from image_generation.backends.model_catalog import InferenceMethod, ModelSpec
from image_generation.config import ImageGenerationConfig
from image_generation.logger import GenerationJobLogger
from image_generation.models import BackendGenerateResult, GenerationRequest


def diffusers_available() -> bool:
    """True if ``torch`` and ``diffusers`` can be imported."""
    return (
        importlib.util.find_spec("torch") is not None
        and importlib.util.find_spec("diffusers") is not None
    )


class DiffusersBackend:
    """Text-to-image via the ``diffusers`` library for one :class:`ModelSpec`."""

    def __init__(
        self,
        spec: ModelSpec,
        config: ImageGenerationConfig,
        *,
        device: str | None = None,
        logger: GenerationJobLogger | None = None,
    ) -> None:
        if spec.method is not InferenceMethod.DIFFUSERS:
            raise ValueError(f"{spec.model_id} is not a diffusers model")
        self._spec = spec
        self._config = config
        self._device = device
        self._log = logger or GenerationJobLogger()
        self._pipe = None
        self._ready = False
        self._error: str | None = None
        self._cancelled: set[str] = set()

    # ---- identity -------------------------------------------------------- #

    def backend_name(self) -> str:
        return f"diffusers:{self._spec.model_id}"

    def version(self) -> str:
        return "diffusers-1.0"

    # ---- lifecycle ------------------------------------------------------- #

    def initialize(self) -> None:
        if not diffusers_available():
            self._error = "torch/diffusers not installed"
            self._ready = False
            self._log.info("DIFFUSERS_UNAVAILABLE", model=self._spec.model_id, reason=self._error)
            return
        try:
            self._pipe = self._load_pipeline()
            self._ready = True
            self._log.info(
                "DIFFUSERS_READY",
                model=self._spec.model_id,
                repo=self._spec.repo_id,
                device=self._resolve_device(),
            )
        except Exception as exc:  # noqa: BLE001 — model download / VRAM failures
            self._error = str(exc)
            self._ready = False
            self._log.error("DIFFUSERS_INIT_FAIL", model=self._spec.model_id, error=self._error)

    def _resolve_device(self) -> str:
        if self._device:
            return self._device
        import torch  # local import — guarded by diffusers_available

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_pipeline(self):
        import torch
        import diffusers

        pipeline_cls = getattr(diffusers, self._spec.pipeline)
        device = self._resolve_device()
        dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
        pipe = pipeline_cls.from_pretrained(self._spec.repo_id, torch_dtype=dtype)
        if device == "cuda":
            # Offload keeps large FLUX/SDXL checkpoints within VRAM budget.
            try:
                pipe.enable_model_cpu_offload()
            except Exception:  # noqa: BLE001
                pipe = pipe.to(device)
        else:
            pipe = pipe.to(device)
        return pipe

    def shutdown(self) -> None:
        self._pipe = None
        self._ready = False
        self._cancelled.clear()

    # ---- generation ------------------------------------------------------ #

    def generate(self, request: GenerationRequest) -> BackendGenerateResult:
        if not self._ready or self._pipe is None:
            return BackendGenerateResult(
                success=False,
                message="DiffusersBackend not ready",
                error=self._error or "BackendNotReady",
            )
        job_hint = str(request.request_id)
        if job_hint in self._cancelled:
            self._cancelled.discard(job_hint)
            return BackendGenerateResult(success=False, message="Cancelled", error="cancelled")

        try:
            image = self._run(request)
            out_path = self._write_png(image, request)
            return BackendGenerateResult(
                success=True,
                message="Image generated",
                output_path=str(out_path),
                metadata={
                    "backend": self.backend_name(),
                    "model_id": self._spec.model_id,
                    "repo_id": self._spec.repo_id,
                    "method": self._spec.method.value,
                    "width": self._spec.width,
                    "height": self._spec.height,
                    "steps": self._spec.steps,
                    "guidance_scale": self._spec.guidance_scale,
                    "device": self._resolve_device(),
                    "seed": request.seed,
                    "style_id": request.style_id,
                },
            )
        except Exception as exc:  # noqa: BLE001 — backend boundary
            self._log.error("DIFFUSERS_GENERATE_FAIL", model=self._spec.model_id, error=str(exc))
            return BackendGenerateResult(success=False, message="Generation failed", error=str(exc))

    def _run(self, request: GenerationRequest):
        import torch

        spec = self._spec
        device = self._resolve_device()
        generator = None
        if request.seed is not None:
            generator = torch.Generator(device=device if device != "mps" else "cpu")
            generator = generator.manual_seed(int(request.seed))

        kwargs = {
            "prompt": request.prompt,
            "width": spec.width,
            "height": spec.height,
            "num_inference_steps": spec.steps,
            "guidance_scale": spec.guidance_scale,
        }
        if generator is not None:
            kwargs["generator"] = generator
        if request.negative_prompt and not spec.is_flux:
            kwargs["negative_prompt"] = request.negative_prompt

        result = self._pipe(**kwargs)
        return result.images[0]

    def cancel(self, job_id: str) -> bool:
        self._cancelled.add(str(job_id))
        return True

    def _write_png(self, image, request: GenerationRequest) -> Path:
        out_dir = self._config.output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = (request.asset_semantic_name or "asset").strip().replace(" ", "_")
        stem = "".join(c for c in stem if c.isalnum() or c in ("_", "-")) or "asset"
        name = f"{stem}_{self._spec.model_id}_{uuid4().hex[:8]}.png"
        path = out_dir / name
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        path.write_bytes(buffer.getvalue())
        return path.resolve()

    # ---- health ---------------------------------------------------------- #

    def health(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_name(),
            "ready": self._ready,
            "model_id": self._spec.model_id,
            "repo_id": self._spec.repo_id,
            "method": self._spec.method.value,
            "dependencies_installed": diffusers_available(),
            "device": self._resolve_device() if diffusers_available() else "n/a",
            "error": self._error,
            "version": self.version(),
        }

    def supported_styles(self) -> Sequence[str]:
        return list(self._config.supported_styles)

    def supported_sizes(self) -> Sequence[tuple[int, int]]:
        return [(self._spec.width, self._spec.height)]
