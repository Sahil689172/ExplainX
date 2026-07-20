"""Declarative catalog of preferred image-generation models (Task 4).

Models are selected by *id* through configuration; the pipeline never hardcodes
a checkpoint at a call site. Priority order matches the requested preference:

    1. flux-dev        (FLUX.1-dev)        — highest quality, slow
    2. flux-schnell    (FLUX.1-schnell)    — fast FLUX, few steps
    3. sdxl-turbo      (SDXL Turbo)        — 1-4 step real-time SDXL
    4. juggernaut-xl   (Juggernaut XL)     — photoreal SDXL finetune
    5. dreamshaper-xl  (DreamShaper XL)    — versatile SDXL finetune

Each entry declares which inference method it prefers (``diffusers`` local or
``comfyui`` remote) plus sensible default resolution / steps / guidance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class InferenceMethod(str, Enum):
    DIFFUSERS = "diffusers"
    COMFYUI = "comfyui"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Everything needed to instantiate a model on a backend."""

    model_id: str                 # stable local id used in config
    repo_id: str                  # HuggingFace repo / ComfyUI checkpoint name
    method: InferenceMethod
    pipeline: str                 # diffusers pipeline class name
    width: int = 1024
    height: int = 1024
    steps: int = 28
    guidance_scale: float = 3.5
    is_flux: bool = False
    notes: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)


MODEL_CATALOG: dict[str, ModelSpec] = {
    "flux-dev": ModelSpec(
        model_id="flux-dev",
        repo_id="black-forest-labs/FLUX.1-dev",
        method=InferenceMethod.DIFFUSERS,
        pipeline="FluxPipeline",
        width=1024,
        height=1024,
        steps=28,
        guidance_scale=3.5,
        is_flux=True,
        notes="Highest fidelity; requires ~24GB VRAM or offloading.",
        aliases=("flux.1-dev", "flux1-dev", "flux"),
    ),
    "flux-schnell": ModelSpec(
        model_id="flux-schnell",
        repo_id="black-forest-labs/FLUX.1-schnell",
        method=InferenceMethod.DIFFUSERS,
        pipeline="FluxPipeline",
        width=1024,
        height=1024,
        steps=4,
        guidance_scale=0.0,
        is_flux=True,
        notes="Distilled FLUX; 1-4 steps, no CFG.",
        aliases=("flux.1-schnell", "flux1-schnell", "schnell"),
    ),
    "sdxl-turbo": ModelSpec(
        model_id="sdxl-turbo",
        repo_id="stabilityai/sdxl-turbo",
        method=InferenceMethod.DIFFUSERS,
        pipeline="AutoPipelineForText2Image",
        width=1024,
        height=1024,
        steps=4,
        guidance_scale=0.0,
        notes="Real-time SDXL; 1-4 steps, guidance 0.",
        aliases=("sdxlturbo", "turbo"),
    ),
    "juggernaut-xl": ModelSpec(
        model_id="juggernaut-xl",
        repo_id="RunDiffusion/Juggernaut-XL-v9",
        method=InferenceMethod.DIFFUSERS,
        pipeline="StableDiffusionXLPipeline",
        width=1024,
        height=1024,
        steps=30,
        guidance_scale=6.0,
        notes="Photoreal SDXL finetune.",
        aliases=("juggernaut", "juggernautxl"),
    ),
    "dreamshaper-xl": ModelSpec(
        model_id="dreamshaper-xl",
        repo_id="Lykon/dreamshaper-xl-1-0",
        method=InferenceMethod.DIFFUSERS,
        pipeline="StableDiffusionXLPipeline",
        width=1024,
        height=1024,
        steps=30,
        guidance_scale=6.0,
        notes="Versatile SDXL finetune; good for illustration.",
        aliases=("dreamshaper", "dreamshaperxl"),
    ),
}

# Highest quality first — the factory walks this list and picks the first
# backend that is actually available.
DEFAULT_PRIORITY: tuple[str, ...] = (
    "flux-dev",
    "flux-schnell",
    "sdxl-turbo",
    "juggernaut-xl",
    "dreamshaper-xl",
)

_ALIAS_INDEX: dict[str, str] = {}
for _spec in MODEL_CATALOG.values():
    _ALIAS_INDEX[_spec.model_id] = _spec.model_id
    for _alias in _spec.aliases:
        _ALIAS_INDEX[_alias.lower()] = _spec.model_id


def get_model_spec(model_id: str) -> ModelSpec:
    """Resolve a model id or alias to its :class:`ModelSpec`."""
    key = str(model_id).strip().lower()
    canonical = _ALIAS_INDEX.get(key)
    if canonical is None:
        raise KeyError(
            f"Unknown model id {model_id!r}. Known: {sorted(MODEL_CATALOG)}"
        )
    return MODEL_CATALOG[canonical]
