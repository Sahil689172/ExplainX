"""Asset Processor configuration (Phase 4.6)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Package root: backend/asset_processor/
_PACKAGE_DIR = Path(__file__).resolve().parent
# Backend root: backend/
_BACKEND_ROOT = _PACKAGE_DIR.parent

# Default directories relative to backend/
DEFAULT_RAW_DIRECTORY = _BACKEND_ROOT / "raw_assets"
DEFAULT_OUTPUT_DIRECTORY = _BACKEND_ROOT / "processed_assets"
DEFAULT_CACHE_DIRECTORY = _BACKEND_ROOT / "cache"

# Preferred: Bria RMBG 2.0 (gated — needs HF login + accepted terms).
# Automatic fallbacks: RMBG-1.4 → rembg/u2net (public).
MODEL_NAME = "briaai/RMBG-2.0"
MODEL_REVISION = "main"

TARGET_SIZE = 512
PIPELINE_VERSION = "4.6.0"

SUPPORTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"})

MIN_DIMENSION = 8
MAX_DIMENSION = 8192


@dataclass(frozen=True, slots=True)
class AssetProcessorConfig:
    """Runtime configuration for the asset processing pipeline."""

    model_name: str = MODEL_NAME
    model_revision: str = MODEL_REVISION
    target_size: int = TARGET_SIZE
    raw_directory: Path = DEFAULT_RAW_DIRECTORY
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY
    cache_directory: Path = DEFAULT_CACHE_DIRECTORY
    min_dimension: int = MIN_DIMENSION
    max_dimension: int = MAX_DIMENSION
    remove_background: bool = True
    require_transparency: bool = False
    use_stub_remover: bool = False  # heuristic remover for tests / offline CI
    pipeline_version: str = PIPELINE_VERSION
    device: str = "cpu"  # CPU optimized; "cuda" if available and desired

    def ensure_directories(self) -> None:
        self.raw_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
