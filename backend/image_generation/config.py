"""Configuration for the Image Generation Engine — no hardcoded call-site values."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


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
    # Future model paths — placeholders only; never loaded in Phase 5.1
    future_model_paths: dict[str, str] = field(
        default_factory=lambda: {
            "openvino": "",
            "diffusers": "",
            "onnx": "",
            "flux": "",
            "sdxl": "",
        }
    )
    engine_version: str = "5.1.0"
    log_level: str = "INFO"

    @classmethod
    def from_defaults(cls) -> ImageGenerationConfig:
        return cls()

    def is_resolution_supported(self, width: int, height: int) -> bool:
        return (width, height) in self.supported_resolutions

    def is_style_supported(self, style_id: str) -> bool:
        return style_id in self.supported_styles

    def list_resolutions(self) -> Sequence[tuple[int, int]]:
        return self.supported_resolutions
