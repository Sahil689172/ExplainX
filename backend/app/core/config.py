"""Application settings loaded from environment variables."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    """Resolve repository root from backend/app/core/config.py."""
    return Path(__file__).resolve().parents[3]


class AppEnv(str, Enum):
    """Runtime environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Central configuration for ExplainX backend.

    Values are loaded from process env and optional `.env` at the repo root.
    Prefix: ``EXPLAINX_``.
    """

    model_config = SettingsConfigDict(
        env_prefix="EXPLAINX_",
        env_file=str(_repo_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    env: AppEnv = AppEnv.DEVELOPMENT
    app_name: str = "ExplainX"
    api_version: str = "v1"
    debug: bool = True

    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    data_root: str = "data"
    log_level: str = "INFO"
    log_to_file: bool = True

    database_url: str | None = None

    max_concurrent_jobs: int = 1

    # Local LLM (Ollama) — prefer unprefixed OLLAMA_* env vars.
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "EXPLAINX_OLLAMA_BASE_URL"),
    )
    ollama_model: str = Field(
        default="qwen2.5:3b",
        validation_alias=AliasChoices("OLLAMA_MODEL", "EXPLAINX_OLLAMA_MODEL"),
        description="Ollama model tag; must be installed locally (ollama pull …).",
    )
    ollama_timeout_sec: float = Field(
        default=600.0,
        ge=5.0,
        le=3600.0,
        validation_alias=AliasChoices(
            "OLLAMA_TIMEOUT",
            "EXPLAINX_OLLAMA_TIMEOUT",
            "EXPLAINX_OLLAMA_TIMEOUT_SEC",
        ),
    )
    ollama_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        validation_alias=AliasChoices(
            "OLLAMA_TEMPERATURE",
            "EXPLAINX_OLLAMA_TEMPERATURE",
        ),
    )
    ollama_enabled: bool = Field(
        default=True,
        description="When false, ContentIntelligenceService uses PlaceholderContentGenerator.",
    )

    # MVP script duration acceptance window (seconds). Metrics still report freely.
    script_min_duration_sec: int = Field(default=60, ge=1, le=3600)
    script_max_duration_sec: int = Field(default=300, ge=1, le=7200)

    # Narration topic verification (deterministic NLP before QA).
    topic_relevance_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "EXPLAINX_TOPIC_RELEVANCE_THRESHOLD",
            "TOPIC_RELEVANCE_THRESHOLD",
        ),
        description="Minimum topic_relevance_score for narration to proceed to QA.",
    )
    topic_verification_max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias=AliasChoices(
            "EXPLAINX_TOPIC_VERIFICATION_MAX_ATTEMPTS",
            "TOPIC_VERIFICATION_MAX_ATTEMPTS",
        ),
        description="Max narration generation attempts when topic verification fails.",
    )

    # Piper TTS (Phase 4 MVP speech generation).
    piper_executable: str = Field(
        default="",
        validation_alias=AliasChoices(
            "PIPER_EXECUTABLE",
            "EXPLAINX_PIPER_EXECUTABLE",
        ),
        description="Path to the Piper TTS executable.",
    )
    piper_voices_dir: str = Field(
        default="data/models/piper",
        validation_alias=AliasChoices(
            "PIPER_VOICES_DIR",
            "EXPLAINX_PIPER_VOICES_DIR",
        ),
        description="Directory of per-language Piper voice folders (en/, hi/, te/).",
    )
    default_language: str = Field(
        default="en",
        validation_alias=AliasChoices(
            "DEFAULT_LANGUAGE",
            "EXPLAINX_DEFAULT_LANGUAGE",
        ),
        description="Fallback language when --lang and script language are missing.",
    )

    # IndicTrans2 offline translation (Phase 4.5).
    indictrans_model: str = Field(
        default="ai4bharat/indictrans2-en-indic-dist-200M",
        validation_alias=AliasChoices(
            "INDICTRANS_MODEL",
            "EXPLAINX_INDICTRANS_MODEL",
        ),
        description="Hugging Face model id for IndicTrans2 EN→Indic translation.",
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        level = value.upper().strip()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return level

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.env == AppEnv.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.env == AppEnv.TESTING

    @property
    def is_production(self) -> bool:
        return self.env == AppEnv.PRODUCTION

    @property
    def data_root_path(self) -> Path:
        path = Path(self.data_root)
        if not path.is_absolute():
            path = _repo_root() / path
        return path.resolve()

    @property
    def logs_dir(self) -> Path:
        return self.data_root_path / "logs"

    @property
    def projects_dir(self) -> Path:
        return self.data_root_path / "projects"

    @property
    def models_dir(self) -> Path:
        return self.data_root_path / "models"

    @property
    def outputs_dir(self) -> Path:
        return self.data_root_path / "outputs"

    @property
    def cache_dir(self) -> Path:
        return self.data_root_path / "cache"

    @property
    def backups_dir(self) -> Path:
        return self.data_root_path / "backups"

    @property
    def resolved_database_url(self) -> str:
        """Return configured DB URL, defaulting to SQLite under data root."""
        if self.database_url:
            return self.database_url
        db_path = (self.data_root_path / "explainx.db").as_posix()
        return f"sqlite:///{db_path}"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for DI."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear settings cache (used by tests)."""
    get_settings.cache_clear()
