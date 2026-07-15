"""Compatibility shim — prefer translation.providers.argos."""

from app.features.translation.providers.argos import (  # noqa: F401
    SUPPORTED_TARGETS,
    ArgosProvider,
    TranslationFailedError,
    TranslationNotInstalledError,
    get_argos_provider,
    reset_argos_provider,
)

# Historical aliases
ArgosEngine = ArgosProvider
get_argos_engine = get_argos_provider
reset_argos_engine = reset_argos_provider
