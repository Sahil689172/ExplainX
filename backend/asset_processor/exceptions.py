"""Custom exceptions for the Asset Processing Pipeline."""

from __future__ import annotations


class AssetProcessorError(Exception):
    """Base error for the asset processing pipeline."""

    def __init__(self, message: str, *, code: str = "ASSET_PROCESSOR_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ImageLoadError(AssetProcessorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="IMAGE_LOAD_ERROR")


class BackgroundRemovalError(AssetProcessorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="BACKGROUND_REMOVAL_ERROR")


class ValidationError(AssetProcessorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="ASSET_VALIDATION_ERROR")


class CacheError(AssetProcessorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="ASSET_CACHE_ERROR")


class UnsupportedFormatError(ValidationError):
    def __init__(self, message: str) -> None:
        AssetProcessorError.__init__(self, message, code="UNSUPPORTED_FORMAT")
