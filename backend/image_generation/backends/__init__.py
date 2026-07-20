"""Interchangeable high-quality image backends (Task 4).

The engine already defines an :class:`~image_generation.interfaces.ImageBackend`
protocol and a :class:`~image_generation.backend_registry.BackendRegistry`.
This subpackage adds production-grade, swappable backends on top of that
contract without touching call sites:

* :mod:`model_catalog` — declarative registry of preferred models
  (FLUX.1-dev, FLUX.1-schnell, SDXL Turbo, Juggernaut XL, DreamShaper XL) and
  the inference method each uses.
* :mod:`diffusers_backend` — HuggingFace ``diffusers`` local inference.
* :mod:`comfyui_backend` — remote ComfyUI HTTP API.
* :mod:`factory` — build a registry that prefers the highest-quality *available*
  backend and transparently falls back to OpenVINO / Null.

Backends that need optional dependencies or model weights report
``health()["ready"] = False`` when unavailable, so selection degrades
gracefully instead of crashing.
"""

from image_generation.backends.model_catalog import (
    DEFAULT_PRIORITY,
    InferenceMethod,
    ModelSpec,
    MODEL_CATALOG,
    get_model_spec,
)

__all__ = [
    "DEFAULT_PRIORITY",
    "InferenceMethod",
    "ModelSpec",
    "MODEL_CATALOG",
    "get_model_spec",
]
