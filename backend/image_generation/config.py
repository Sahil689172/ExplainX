"""Configuration for the Image Generation Engine — no hardcoded call-site values."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


def _backend_root() -> Path:
    """``backend/`` directory (parent of ``image_generation`` package)."""
    return Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class ImageGenerationConfig:
    """Engine configuration. Prefer constructing via ``from_defaults`` or DI."""

    default_backend_id: str = "null"
    timeout_seconds: float = 120.0
    retry_count: int = 1
    max_queue_size: int = 256
    null_backend_sleep_seconds: float = 0.05
    supported_resolutions: tuple[tuple[int, int], ...] = (
        (256, 256),
        (512, 512),
        (768, 768),
        (1024, 1024),
        (512, 768),
        (768, 512),
        (1280, 720),
        (720, 1280),
    )
    supported_styles: tuple[str, ...] = (
        "flat",
        "blueprint",
        "chalkboard",
        "whiteboard",
        "cartoon",
        "minimal_vector",
    )
    supported_aspect_ratios: tuple[str, ...] = (
        "1:1",
        "4:3",
        "3:4",
        "16:9",
        "9:16",
    )
    supported_output_formats: tuple[str, ...] = ("png", "webp", "jpeg")
    # Optional future backend paths — OpenVINO SD1.5 is Phase 5.2 only model
    future_model_paths: dict[str, str] = field(
        default_factory=lambda: {
            "openvino": "models/openvino_sd15",
            "diffusers": "",
            "onnx": "",
            "flux": "",
            "sdxl": "",
        }
    )
    engine_version: str = "5.2.0"
    log_level: str = "INFO"

    # --- Phase 5.2 OpenVINO / official SD 1.5 FP16 IR ---
    openvino_model_repo_id: str = "OpenVINO/stable-diffusion-v1-5-fp16-ov"
    openvino_model_path: str = "models/openvino_sd15"
    openvino_cache_path: str = "models/cache"
    openvino_output_dir: str = "generated/raw"
    openvino_device_preference: tuple[str, ...] = ("GPU", "CPU")
    openvino_seed: int = 42
    openvino_scheduler: str = "default"
    openvino_inference_steps: int = 20
    openvino_guidance_scale: float = 7.5
    openvino_width: int = 512
    openvino_height: int = 512
    openvino_warmup_on_load: bool = True
    openvino_warmup_steps: int = 2
    openvino_allow_download: bool = True
    openvino_backend_version: str = "5.2.0"

    @classmethod
    def from_defaults(cls) -> ImageGenerationConfig:
        return cls()

    def resolve_path(self, path: str | Path) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (_backend_root() / p).resolve()

    def model_dir(self) -> Path:
        return self.resolve_path(self.openvino_model_path)

    def cache_dir(self) -> Path:
        return self.resolve_path(self.openvino_cache_path)

    def output_dir(self) -> Path:
        return self.resolve_path(self.openvino_output_dir)

    def is_resolution_supported(self, width: int, height: int) -> bool:
        return (width, height) in self.supported_resolutions

    def is_style_supported(self, style_id: str) -> bool:
        return style_id in self.supported_styles

    def list_resolutions(self) -> Sequence[tuple[int, int]]:
        return self.supported_resolutions
