"""Domain exceptions for the Image Generation Engine."""

from __future__ import annotations


class ImageGenerationError(Exception):
    """Base error for the engine."""


class ValidationError(ImageGenerationError):
    """Request failed validation."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class BackendNotFoundError(ImageGenerationError):
    """Requested backend is not registered."""


class BackendNotReadyError(ImageGenerationError):
    """Backend exists but is not initialized / unhealthy."""


class QueueFullError(ImageGenerationError):
    """Generation queue rejected enqueue due to capacity."""


class JobNotFoundError(ImageGenerationError):
    """Job id not found in queue or tracker."""


class JobCancelledError(ImageGenerationError):
    """Job was cancelled before or during execution."""


class GenerationFailedError(ImageGenerationError):
    """Backend reported failure during generate()."""


class ModelNotFoundError(ImageGenerationError):
    """Configured OpenVINO model directory is missing or incomplete."""


class ModelDownloadError(ImageGenerationError):
    """Hugging Face model download failed after retries."""


class ModelLoadError(ImageGenerationError):
    """Model / pipeline failed to load on the selected device."""


class DeviceInitError(ImageGenerationError):
    """Neither GPU nor CPU device could initialize the pipeline."""
