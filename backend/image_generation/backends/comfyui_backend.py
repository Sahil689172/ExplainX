"""ComfyUIBackend — remote ComfyUI HTTP API inference (Task 4).

Talks to a running ComfyUI server (``--listen``) over its REST API. The backend
is ``ready`` only when the server responds, so it is safe to register alongside
local backends and let the factory pick whatever is actually up.

Uses only the standard library (``urllib``, ``json``) — no extra dependencies.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from image_generation.backends.model_catalog import ModelSpec
from image_generation.config import ImageGenerationConfig
from image_generation.logger import GenerationJobLogger
from image_generation.models import BackendGenerateResult, GenerationRequest


class ComfyUIBackend:
    """Text-to-image via a remote ComfyUI server."""

    def __init__(
        self,
        spec: ModelSpec,
        config: ImageGenerationConfig,
        *,
        server_url: str = "http://127.0.0.1:8188",
        checkpoint: str | None = None,
        timeout: float = 120.0,
        logger: GenerationJobLogger | None = None,
    ) -> None:
        self._spec = spec
        self._config = config
        self._server = server_url.rstrip("/")
        self._checkpoint = checkpoint or f"{spec.model_id}.safetensors"
        self._timeout = timeout
        self._log = logger or GenerationJobLogger()
        self._ready = False
        self._error: str | None = None

    def backend_name(self) -> str:
        return f"comfyui:{self._spec.model_id}"

    def version(self) -> str:
        return "comfyui-1.0"

    def _server_up(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self._server}/system_stats", timeout=3) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def initialize(self) -> None:
        self._ready = self._server_up()
        if not self._ready:
            self._error = f"ComfyUI server not reachable at {self._server}"
        self._log.info("COMFYUI_INIT", server=self._server, ready=self._ready)

    def shutdown(self) -> None:
        self._ready = False

    # ---- workflow -------------------------------------------------------- #

    def _build_workflow(self, request: GenerationRequest) -> dict[str, Any]:
        spec = self._spec
        seed = int(request.seed) if request.seed is not None else uuid4().int % (2**32)
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": spec.steps,
                    "cfg": spec.guidance_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": self._checkpoint}},
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": spec.width, "height": spec.height, "batch_size": 1},
            },
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": request.prompt, "clip": ["4", 1]}},
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": request.negative_prompt or "", "clip": ["4", 1]},
            },
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "explainx", "images": ["8", 0]},
            },
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._server}{path}", data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_json(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(f"{self._server}{path}", timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def generate(self, request: GenerationRequest) -> BackendGenerateResult:
        if not self._ready:
            return BackendGenerateResult(
                success=False, message="ComfyUIBackend not ready", error=self._error or "BackendNotReady"
            )
        try:
            workflow = self._build_workflow(request)
            submit = self._post("/prompt", {"prompt": workflow, "client_id": uuid4().hex})
            prompt_id = submit["prompt_id"]
            image_info = self._await_image(prompt_id)
            out_path = self._download_image(image_info, request)
            return BackendGenerateResult(
                success=True,
                message="Image generated",
                output_path=str(out_path),
                metadata={
                    "backend": self.backend_name(),
                    "model_id": self._spec.model_id,
                    "server": self._server,
                    "checkpoint": self._checkpoint,
                    "prompt_id": prompt_id,
                    "width": self._spec.width,
                    "height": self._spec.height,
                    "steps": self._spec.steps,
                },
            )
        except Exception as exc:  # noqa: BLE001 — backend boundary
            self._log.error("COMFYUI_GENERATE_FAIL", error=str(exc))
            return BackendGenerateResult(success=False, message="Generation failed", error=str(exc))

    def _await_image(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            history = self._get_json(f"/history/{prompt_id}")
            entry = history.get(prompt_id)
            if entry and entry.get("outputs"):
                for node in entry["outputs"].values():
                    images = node.get("images")
                    if images:
                        return images[0]
            time.sleep(1.0)
        raise TimeoutError(f"ComfyUI did not return an image within {self._timeout}s")

    def _download_image(self, image_info: dict[str, Any], request: GenerationRequest) -> Path:
        params = urllib.parse.urlencode(
            {
                "filename": image_info["filename"],
                "subfolder": image_info.get("subfolder", ""),
                "type": image_info.get("type", "output"),
            }
        )
        with urllib.request.urlopen(f"{self._server}/view?{params}", timeout=self._timeout) as resp:
            data = resp.read()
        out_dir = self._config.output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = (request.asset_semantic_name or "asset").strip().replace(" ", "_")
        stem = "".join(c for c in stem if c.isalnum() or c in ("_", "-")) or "asset"
        path = out_dir / f"{stem}_comfy_{uuid4().hex[:8]}.png"
        path.write_bytes(data)
        return path.resolve()

    def cancel(self, job_id: str) -> bool:
        return False

    def health(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_name(),
            "ready": self._ready,
            "server": self._server,
            "checkpoint": self._checkpoint,
            "model_id": self._spec.model_id,
            "error": self._error,
            "version": self.version(),
        }

    def supported_styles(self) -> Sequence[str]:
        return list(self._config.supported_styles)

    def supported_sizes(self) -> Sequence[tuple[int, int]]:
        return [(self._spec.width, self._spec.height)]
