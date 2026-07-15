"""TranslationService — English narration → target language with disk cache."""

from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.features.narration.languages import (
    SUPPORTED_OUTPUT_LANGUAGES,
    language_label,
    normalize_output_language,
)
from app.features.narration.store import NarrationArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.quality.store import QualityArtifactStore
from app.features.translation.providers.argos import TranslationFailedError
from app.features.translation.providers.base import TranslationProvider
from app.features.translation.providers.factory import create_translation_provider

logger = get_logger(__name__)

# Languages that may be requested for output (en is passthrough).
SUPPORTED_LANGS = SUPPORTED_OUTPUT_LANGUAGES


class TranslationService:
    """Translate English narration after script generation; cache ``narration_<lang>.txt``."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        provider: TranslationProvider | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._narration_store = NarrationArtifactStore(self._fs)
        self._quality_store = QualityArtifactStore(self._fs)
        self._provider_lazy: TranslationProvider | None = provider

    @property
    def _provider(self) -> TranslationProvider:
        if self._provider_lazy is None:
            self._provider_lazy = create_translation_provider(self._settings)
        return self._provider_lazy

    def artifacts_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts"

    def narration_path(self, project_id: str, lang: str) -> Path:
        """Path to ``artifacts/narration_<lang>.txt``."""
        code = normalize_output_language(lang)
        return self.artifacts_dir(project_id) / f"narration_{code}.txt"

    def load_english_source(self, project_id: str) -> str:
        """Prefer ``narration_en.txt`` / legacy ``narration.txt``, then approved script / JSON."""
        text = self._narration_store.read_text(project_id, "en")
        if text and text.strip():
            return text.strip()

        approved_path = self._quality_store.approved_script_path(project_id)
        if approved_path.is_file():
            script = self._quality_store.read_approved(project_id)
            approved = (script.full_text or "").strip()
            if approved:
                return approved

        narration = self._narration_store.read(project_id)
        body = (narration.text or "").strip()
        if not body:
            raise NotFoundError(
                "No English narration text available to translate.",
                code="NARRATION_NOT_FOUND",
                details={"project_id": project_id},
            )
        return body

    def ensure_translated(self, project_id: str, lang: str) -> str:
        """Return narration text for ``lang``, translating from English when needed.

        Cache:
        - Always ensure ``artifacts/narration_en.txt`` exists.
        - Reuse ``artifacts/narration_<lang>.txt`` when present (Cache : Hit).
        """
        validate_project_id(project_id)
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )

        try:
            code = normalize_output_language(lang)
        except ValidationAppError:
            raise ValidationAppError(
                f"Unsupported language for translation: {lang!r}.",
                code="LANGUAGE_NOT_SUPPORTED",
                details={
                    "language": lang,
                    "supported_languages": list(SUPPORTED_LANGS),
                },
            ) from None

        out_dir = self.artifacts_dir(project_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        en_path = self.narration_path(project_id, "en")
        if en_path.is_file() and en_path.stat().st_size > 0:
            english = en_path.read_text(encoding="utf-8").strip()
        else:
            english = self.load_english_source(project_id)
            en_path.write_text(english + ("\n" if not english.endswith("\n") else ""), encoding="utf-8")
            # Keep store paths / legacy narration.txt in sync when missing.
            self._narration_store.write_text(project_id, "en", english)

        if code == "en":
            self._log_translation(
                source="en",
                target="en",
                elapsed_sec=0.0,
                cache="Hit",
            )
            return english

        target_path = self.narration_path(project_id, code)
        if target_path.is_file() and target_path.stat().st_size > 0:
            text = target_path.read_text(encoding="utf-8").strip()
            if not text:
                raise TranslationFailedError(
                    "Cached translation is empty.",
                    details={"language": code, "path": str(target_path)},
                )
            self._log_translation(
                source="en",
                target=code,
                elapsed_sec=0.0,
                cache="Hit",
            )
            return text

        if not self._provider.supports(code):
            raise ValidationAppError(
                f"Translation provider does not support {code!r}.",
                code="LANGUAGE_NOT_SUPPORTED",
                details={
                    "language": code,
                    "provider": self._provider.name,
                },
            )

        started = time.perf_counter()
        translated = self._provider.translate(english, target_lang=code)
        elapsed = time.perf_counter() - started
        if not translated.strip():
            raise TranslationFailedError(
                "Translation produced empty output.",
                details={"language": code},
            )

        target_path.write_text(
            translated + ("\n" if not translated.endswith("\n") else ""),
            encoding="utf-8",
        )
        self._log_translation(
            source="en",
            target=code,
            elapsed_sec=elapsed,
            cache="Miss",
        )
        logger.info(
            "Translation saved",
            extra={
                "event": "translation_saved",
                "project_id": project_id,
                "language": code,
                "path": str(target_path),
                "elapsed_sec": round(elapsed, 3),
                "provider": self._provider.name,
                "cache": "Miss",
            },
        )
        return translated

    def _log_translation(
        self,
        *,
        source: str,
        target: str,
        elapsed_sec: float,
        cache: str,
    ) -> None:
        src_label = language_label(source)
        tgt_label = language_label(target)
        print("[Translation]", flush=True)
        print(f"{src_label} → {tgt_label}", flush=True)
        print(f"Time : {elapsed_sec:.2f} sec", flush=True)
        print(f"Cache : {cache}", flush=True)
        print(f"Provider : {self._provider.name}", flush=True)
