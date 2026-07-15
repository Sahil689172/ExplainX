"""Factory for offline translation providers."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.features.translation.providers.argos import ArgosProvider, get_argos_provider
from app.features.translation.providers.base import TranslationProvider

_REPO_ROOT = Path(__file__).resolve().parents[5]


def resolve_argos_models_dir(settings: Settings) -> Path:
    configured = getattr(settings, "argos_models_dir", None) or "data/models/argos"
    path = Path(str(configured))
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path.resolve()


def create_translation_provider(settings: Settings) -> TranslationProvider:
    """Build the configured offline translation provider (Argos by default).

    Swap this factory to MarianMT / NLLB / IndicTrans without changing
    TranslationService.
    """
    models_dir = resolve_argos_models_dir(settings)
    return get_argos_provider(models_dir=models_dir)


# Re-export for type checkers / tests.
__all__ = [
    "ArgosProvider",
    "TranslationProvider",
    "create_translation_provider",
    "resolve_argos_models_dir",
]
