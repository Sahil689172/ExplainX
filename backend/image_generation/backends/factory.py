"""Backend factory — pick the best *available* image backend (Task 4).

Walks the configured priority list (FLUX.1-dev → FLUX.1-schnell → SDXL Turbo →
Juggernaut XL → DreamShaper XL), initializing each candidate. The first backend
that reports ``ready`` becomes the default. If none are available the factory
registers the OpenVINO and Null fallbacks so the pipeline still runs.

Nothing here imports ``torch``/``diffusers`` eagerly — availability is probed
through the backends themselves, which short-circuit when dependencies or model
weights are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from image_generation.backend_registry import BackendRegistry
from image_generation.backends.comfyui_backend import ComfyUIBackend
from image_generation.backends.diffusers_backend import DiffusersBackend
from image_generation.backends.model_catalog import (
    DEFAULT_PRIORITY,
    InferenceMethod,
    get_model_spec,
)
from image_generation.config import ImageGenerationConfig
from image_generation.logger import GenerationJobLogger


@dataclass(slots=True)
class ImageBackendConfig:
    """Model-selection configuration (Task 4: 'model selection through config')."""

    priority: tuple[str, ...] = DEFAULT_PRIORITY
    method: str = "auto"  # "auto" | "diffusers" | "comfyui"
    comfyui_url: str = "http://127.0.0.1:8188"
    device: str | None = None
    allow_openvino_fallback: bool = True


@dataclass(slots=True)
class BackendSelection:
    """What the factory produced."""

    registry: BackendRegistry
    selected_id: str | None
    report: list[dict[str, object]] = field(default_factory=list)

    @property
    def using_high_quality(self) -> bool:
        return bool(self.selected_id) and self.selected_id.startswith(("diffusers:", "comfyui:"))


def _make_backend(model_id: str, cfg: ImageGenerationConfig, bcfg: ImageBackendConfig):
    spec = get_model_spec(model_id)
    method = bcfg.method.lower()
    if method == "auto":
        method = spec.method.value
    if method == InferenceMethod.COMFYUI.value:
        return ComfyUIBackend(spec, cfg, server_url=bcfg.comfyui_url)
    return DiffusersBackend(spec, cfg, device=bcfg.device)


def build_image_backend_registry(
    config: ImageGenerationConfig | None = None,
    backend_config: ImageBackendConfig | None = None,
    *,
    logger: GenerationJobLogger | None = None,
) -> BackendSelection:
    cfg = config or ImageGenerationConfig.from_defaults()
    bcfg = backend_config or ImageBackendConfig()
    log = logger or GenerationJobLogger()

    registry = BackendRegistry()
    report: list[dict[str, object]] = []
    selected_id: str | None = None

    for model_id in bcfg.priority:
        try:
            backend = _make_backend(model_id, cfg, bcfg)
        except Exception as exc:  # noqa: BLE001
            report.append({"model": model_id, "ready": False, "error": str(exc)})
            continue

        backend.initialize()
        health = backend.health()
        ready = bool(health.get("ready"))
        registry.register(backend, set_as_default=False)
        report.append(
            {
                "model": model_id,
                "backend": backend.backend_name(),
                "ready": ready,
                "error": health.get("error"),
            }
        )
        if ready and selected_id is None:
            selected_id = backend.backend_name()
            registry.set_default(selected_id)
            log.info("IMAGE_BACKEND_SELECTED", backend=selected_id, model=model_id)

    # Fallbacks so the pipeline always has a default backend.
    if bcfg.allow_openvino_fallback:
        try:
            from image_generation.openvino import OpenVINOBackend

            ov = OpenVINOBackend(cfg)
            ov.initialize()
            registry.register(ov, set_as_default=selected_id is None)
            ov_ready = bool(ov.health().get("ready"))
            report.append({"model": "openvino", "backend": "openvino", "ready": ov_ready})
            if selected_id is None and ov_ready:
                selected_id = "openvino"
                registry.set_default(selected_id)
        except Exception as exc:  # noqa: BLE001
            report.append({"model": "openvino", "ready": False, "error": str(exc)})

    from image_generation.null_backend import NullBackend

    null = NullBackend(cfg)
    registry.register(null, set_as_default=selected_id is None)
    if selected_id is None:
        selected_id = null.backend_name()
        registry.set_default(selected_id)

    log.info("IMAGE_BACKEND_REGISTRY_READY", selected=selected_id, candidates=len(report))
    return BackendSelection(registry=registry, selected_id=selected_id, report=report)
