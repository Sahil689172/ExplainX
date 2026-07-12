"""OllamaRepairGenerator — repair one section narration via Ollama."""

from __future__ import annotations

import json
import re

from app.core.config import Settings
from app.core.errors import ExplainXError
from app.core.logging import get_logger
from app.features.quality.ollama import templates
from app.features.quality.schemas import SectionRepairRequest
from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol

logger = get_logger(__name__)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class OllamaRepairGenerator:
    """Ask Ollama to repair a single section's narration."""

    def __init__(
        self,
        client: OllamaClientProtocol,
        *,
        model_name: str | None = None,
    ) -> None:
        self._client = client
        self._model_name = model_name or getattr(client, "model", "unknown")

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaRepairGenerator:
        client = OllamaClient.from_settings(settings)
        return cls(client, model_name=client.model)

    def repair_section(self, request: SectionRepairRequest) -> str:
        failures = "\n".join(f"- {item}" for item in request.validation_failures) or "(none)"
        user = templates.USER.format(
            action=request.action.value,
            title=request.original_title,
            learning_objective=request.learning_objective or "(none)",
            target_words=request.target_words,
            actual_words=request.actual_words,
            validation_failures=failures,
            previous_section_summary=request.previous_section_summary.strip()
            or "(none)",
            next_section_title=request.next_section_title or "(none)",
            original_narration=request.original_narration[:8_000],
        )
        raw = self._client.generate(system=templates.SYSTEM, prompt=user)
        narration = self._parse_narration(raw)
        logger.info(
            "Ollama section repair completed",
            extra={
                "event": "ollama_section_repaired",
                "component": "ollama_repair_generator",
                "section_id": request.section_id,
                "action": request.action.value,
                "model": self._model_name,
                "prompt_template_version": templates.PROMPT_TEMPLATE_VERSION,
            },
        )
        return narration

    def _parse_narration(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            raise ExplainXError(
                "Ollama returned an empty repair response.",
                code="OLLAMA_EMPTY_RESPONSE",
                status_code=502,
            )
        cleaned = raw_text.strip()
        cleaned = _FENCE_RE.sub("", cleaned).strip()
        if not cleaned.startswith("{"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                cleaned = cleaned[start : end + 1]
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Tolerate bare narration text as a last resort.
            if cleaned and not cleaned.startswith("{"):
                return cleaned.strip()
            raise ExplainXError(
                "Ollama repair response is not valid JSON.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"error": str(exc), "preview": cleaned[:300]},
            ) from exc
        if not isinstance(data, dict):
            raise ExplainXError(
                "Ollama repair JSON root must be an object.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        narration = str(data.get("narration") or "").strip()
        if not narration:
            raise ExplainXError(
                "Ollama repair JSON missing narration.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        return narration
