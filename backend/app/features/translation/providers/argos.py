"""Argos Translate offline EN→Indic provider."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.errors import ExplainXError

# Argos packages available under data/models/argos (extend as installed).
SUPPORTED_TARGETS = frozenset({"hi", "te"})

_lock = threading.Lock()
_engine: ArgosProvider | None = None


class TranslationFailedError(ExplainXError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="TRANSLATION_FAILED",
            status_code=500,
            details=details,
            retriable=False,
        )


class TranslationNotInstalledError(ExplainXError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="TRANSLATION_NOT_INSTALLED",
            status_code=422,
            details=details,
            retriable=False,
        )


class ArgosProvider:
    """Load Argos languages/translations once and reuse in memory."""

    def __init__(self, *, models_dir: Path | None = None) -> None:
        try:
            import argostranslate.package  # noqa: F401
            import argostranslate.translate
        except ImportError as exc:
            raise TranslationFailedError(
                "argostranslate is required. Install with: pip install argostranslate",
                details={"missing": str(exc)},
            ) from exc

        self._package = __import__("argostranslate.package", fromlist=["*"])
        self._translate_mod = __import__("argostranslate.translate", fromlist=["*"])

        if models_dir is not None:
            self._install_local_packages(models_dir)

        self.installed_languages: list[Any] = list(
            self._translate_mod.get_installed_languages()
        )
        self.language_map: dict[str, Any] = {
            lang.code: lang for lang in self.installed_languages
        }
        self.translations: dict[tuple[str, str], Any] = {}
        self._warm_translations()

    @property
    def name(self) -> str:
        return "Argos"

    def supports(self, target_lang: str) -> bool:
        code = (target_lang or "").strip().lower()[:2]
        return code == "en" or code in SUPPORTED_TARGETS

    def _install_local_packages(self, models_dir: Path) -> None:
        """Install any ``*.argosmodel`` files under models_dir (offline, one-time)."""
        if not models_dir.is_dir():
            return
        for path in sorted(models_dir.glob("*.argosmodel")):
            try:
                self._package.install_from_path(path)
            except Exception:
                # Already installed or incompatible — ignore at startup.
                continue

    def _warm_translations(self) -> None:
        from_lang = self.language_map.get("en")
        if from_lang is None:
            return
        for code in SUPPORTED_TARGETS:
            to_lang = self.language_map.get(code)
            if to_lang is None:
                continue
            try:
                translation = from_lang.get_translation(to_lang)
            except Exception:
                continue
            if translation is not None:
                self.translations[("en", code)] = translation

    def get_translation(self, from_code: str, to_code: str) -> Any:
        key = (from_code, to_code)
        if key in self.translations:
            return self.translations[key]

        from_lang = self.language_map.get(from_code)
        to_lang = self.language_map.get(to_code)
        if from_lang is None or to_lang is None:
            raise TranslationNotInstalledError(
                f"Argos language package not installed for {from_code}→{to_code}.",
                details={
                    "source": from_code,
                    "target": to_code,
                    "installed": sorted(self.language_map),
                },
            )

        try:
            translation = from_lang.get_translation(to_lang)
        except Exception as exc:  # noqa: BLE001
            raise TranslationNotInstalledError(
                f"Argos translation {from_code}→{to_code} is not available.",
                details={"source": from_code, "target": to_code, "error": str(exc)},
            ) from exc

        if translation is None:
            raise TranslationNotInstalledError(
                f"Argos language package not installed for {from_code}→{to_code}.",
                details={
                    "source": from_code,
                    "target": to_code,
                    "installed": sorted(self.language_map),
                },
            )

        self.translations[key] = translation
        return translation

    def translate(self, text: str, *, target_lang: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            raise TranslationFailedError(
                "Cannot translate empty text.",
                details={"field": "text"},
            )

        code = (target_lang or "").strip().lower()[:2]
        if code == "en":
            return cleaned
        if code not in SUPPORTED_TARGETS:
            raise TranslationFailedError(
                f"Unsupported translation target: {target_lang!r}. Use hi or te.",
                details={
                    "target_lang": target_lang,
                    "supported": sorted(SUPPORTED_TARGETS),
                },
            )

        translation = self.get_translation("en", code)
        try:
            result = translation.translate(cleaned)
        except Exception as exc:  # noqa: BLE001
            raise TranslationFailedError(
                "Argos translation failed.",
                details={"error": str(exc), "target_lang": code},
            ) from exc

        if result is None or not str(result).strip():
            raise TranslationFailedError(
                "Argos translation returned empty output.",
                details={"language": code},
            )
        return str(result).strip()


def get_argos_provider(*, models_dir: Path | None = None) -> ArgosProvider:
    """Return the process-wide Argos provider (loaded once)."""
    global _engine
    if _engine is not None:
        return _engine
    with _lock:
        if _engine is None:
            _engine = ArgosProvider(models_dir=models_dir)
        return _engine


def reset_argos_provider() -> None:
    """Clear the cached provider (tests only)."""
    global _engine
    with _lock:
        _engine = None
