"""Local image generator — interface only (future AI providers).

Future drop-in providers (do NOT implement here):

* OpenVINOProvider
* ONNXProvider
* GGUFProvider
* StableDiffusionProvider / FluxProvider / FableProvider / RunwareProvider

This class declares capability for illustration/photo scenes but never produces
pixels. The AssetGenerationService will skip it and choose the next deterministic
generator when available.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.services.asset_generation.interfaces import AssetGenerator
from app.services.asset_generation.models import (
    AssetStatus,
    GenerationResult,
    GeneratorType,
)

if TYPE_CHECKING:
    from app.services.visual_intelligence.service import ScenePlan


class LocalImageGenerator(AssetGenerator):
    """AI image generation seam — intentionally unimplemented."""

    def generator_type(self) -> GeneratorType:
        return GeneratorType.LOCAL_IMAGE

    def supports(self, plan: ScenePlan) -> bool:
        # Advertise capability for routing discovery, but ``generate`` never succeeds.
        return plan.intent.visual_type.value in {"illustration", "photo"}

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.0

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 0.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        _ = output_dir
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.LOCAL_IMAGE,
            status=AssetStatus.SKIPPED,
            detail=(
                "LocalImageGenerator is an interface only. "
                "Register a future provider (OpenVINO/ONNX/GGUF/SD) without changing callers."
            ),
        )

    def metadata(self) -> dict[str, Any]:
        data = super().metadata()
        data.update(
            {
                "ai": True,
                "implemented": False,
                "future_providers": [
                    "OpenVINOProvider",
                    "ONNXProvider",
                    "GGUFProvider",
                    "StableDiffusionProvider",
                ],
            }
        )
        return data
