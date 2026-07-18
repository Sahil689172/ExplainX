"""ExplainX Image Generation Engine (Phase 5.1) — orchestration only.

Accepts generation requests, validates, queues jobs, routes to backends,
tracks progress, and returns standardized responses.

Does **not** load AI models or generate images.
"""

from image_generation.config import ImageGenerationConfig
from image_generation.image_generation_service import ImageGenerationService
from image_generation.models import (
    GenerationJob,
    GenerationProgress,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
)

__all__ = [
    "ImageGenerationConfig",
    "ImageGenerationService",
    "GenerationJob",
    "GenerationProgress",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationStatus",
]

ENGINE_VERSION = "5.1.0"
SCHEMA_VERSION = "1.0.0"
