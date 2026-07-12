"""Parse one-section Ollama JSON into SectionOutput."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from app.core.errors import ExplainXError
from app.core.timeutil import utc_now_iso
from app.features.outline.schemas import TeachingSection
from app.features.script.metrics import count_words
from app.features.section_generation.ollama import templates
from app.features.section_generation.schemas import SectionOutput

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class SectionResponseParser:
    def parse(
        self,
        raw_text: str,
        *,
        section: TeachingSection,
        index: int,
        retry_fn: Callable[[str], str] | None = None,
        model_name: str = "unknown",
    ) -> SectionOutput:
        try:
            payload = self._loads(raw_text)
            return self._to_output(
                payload, section=section, index=index, model_name=model_name
            )
        except ExplainXError as first_error:
            if retry_fn is None:
                raise
            repaired = retry_fn(raw_text)
            try:
                payload = self._loads(repaired)
                return self._to_output(
                    payload, section=section, index=index, model_name=model_name
                )
            except ExplainXError as second_error:
                raise ExplainXError(
                    "Ollama returned invalid section JSON after one retry.",
                    code="OLLAMA_INVALID_JSON",
                    status_code=502,
                    details={
                        "first_error": first_error.message,
                        "second_error": second_error.message,
                        "section_id": section.id,
                        "index": index,
                    },
                ) from second_error

    def _loads(self, raw_text: str) -> dict[str, Any]:
        if not raw_text or not raw_text.strip():
            raise ExplainXError(
                "Ollama returned an empty section response.",
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
            raise ExplainXError(
                "Ollama section response is not valid JSON.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"error": str(exc), "preview": cleaned[:300]},
            ) from exc
        if not isinstance(data, dict) or not data:
            raise ExplainXError(
                "Ollama section JSON root must be a non-empty object.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        return data

    def _to_output(
        self,
        payload: dict[str, Any],
        *,
        section: TeachingSection,
        index: int,
        model_name: str,
    ) -> SectionOutput:
        for key in (
            "estimated_words",
            "estimated_duration_sec",
            "target_words",
            "word_count",
        ):
            payload.pop(key, None)

        narration = str(payload.get("narration") or "").strip()
        if not narration:
            raise ExplainXError(
                "Ollama section JSON missing narration.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"section_id": section.id, "index": index},
            )
        summary = str(payload.get("summary") or "").strip()
        if not summary:
            words = narration.split()
            summary = " ".join(words[:28]).rstrip(",;:") + ("…" if len(words) > 28 else ".")

        return SectionOutput(
            outline_section_id=section.id,
            index=index,
            title=section.title,
            narration=narration,
            learning_objective=section.learning_objective,
            key_concepts=list(section.key_concepts),
            target_words=section.target_words,
            summary=summary[:1000],
            warnings=[],
            metadata={
                "generator": "ollama_section_v1",
                "llm": True,
                "ollama_model": model_name,
                "prompt_template_version": templates.PROMPT_TEMPLATE_VERSION,
                "actual_words": count_words(narration),
            },
            created_at=utc_now_iso(),
        )
