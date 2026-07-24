"""Generator plugin contract for the Asset Generation Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.services.asset_generation.models import (
    GenerationResult,
    GeneratorType,
)

if TYPE_CHECKING:
    from app.services.visual_intelligence.service import ScenePlan


class AssetGenerator(ABC):
    """Uniform interface every deterministic (or future AI) generator implements."""

    @abstractmethod
    def generator_type(self) -> GeneratorType:
        """Stable registry id for this plugin."""

    @abstractmethod
    def supports(self, plan: ScenePlan) -> bool:
        """True when this generator can satisfy the ScenePlan deterministically."""

    @abstractmethod
    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        """Produce asset files under ``output_dir`` (must exist)."""

    @abstractmethod
    def estimate_time(self, plan: ScenePlan) -> float:
        """Estimated wall-clock seconds."""

    @abstractmethod
    def estimate_memory(self, plan: ScenePlan) -> float:
        """Estimated peak memory in megabytes."""

    def metadata(self) -> dict[str, Any]:
        """Static discovery descriptor."""
        return {
            "generator": self.generator_type().value,
            "class": type(self).__name__,
            "ai": False,
            "local": True,
        }
