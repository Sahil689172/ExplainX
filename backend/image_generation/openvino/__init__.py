"""OpenVINO backend package (Phase 5.2)."""

from image_generation.openvino.model_manager import ModelManager, ModelStatus
from image_generation.openvino.openvino_backend import OpenVINOBackend
from image_generation.openvino.output_pipeline import (
    AssetOutputPipeline,
    OutputPipelineProtocol,
)

__all__ = [
    "ModelManager",
    "ModelStatus",
    "OpenVINOBackend",
    "AssetOutputPipeline",
    "OutputPipelineProtocol",
]
