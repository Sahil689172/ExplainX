"""Parse Ollama JSON into TeachingOutline (no narration)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

from pydantic import ValidationError

from app.core.errors import ExplainXError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.outline.budget import apply_word_budget
from app.features.outline.ollama import templates
from app.features.outline.schemas import (
    OUTLINE_SECTION_MAX,
    OUTLINE_SECTION_MIN,
    TEACHING_OUTLINE_SCHEMA_VERSION,
    TeachingOutline,
    TeachingSection,
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class OutlineResponseParser:
    def parse(
        self,
        raw_text: str,
        *,
        raw: RawContent,
        target_duration_sec: int,
        total_target_words: int,
        fallback_title: str,
        fallback_language: str,
        retry_fn: Callable[[str], str] | None = None,
    ) -> TeachingOutline:
        try:
            payload = self._loads(raw_text)
            return self._to_outline(
                payload,
                raw=raw,
                target_duration_sec=target_duration_sec,
                total_target_words=total_target_words,
                fallback_title=fallback_title,
                fallback_language=fallback_language,
            )
        except ExplainXError as first_error:
            if retry_fn is None:
                raise
            repaired = retry_fn(raw_text)
            try:
                payload = self._loads(repaired)
                return self._to_outline(
                    payload,
                    raw=raw,
                    target_duration_sec=target_duration_sec,
                    total_target_words=total_target_words,
                    fallback_title=fallback_title,
                    fallback_language=fallback_language,
                )
            except ExplainXError as second_error:
                raise ExplainXError(
                    "Ollama returned invalid TeachingOutline JSON after one retry.",
                    code="OLLAMA_INVALID_JSON",
                    status_code=502,
                    details={
                        "first_error": first_error.message,
                        "second_error": second_error.message,
                    },
                ) from second_error

    def _loads(self, raw_text: str) -> dict[str, Any]:
        if not raw_text or not raw_text.strip():
            raise ExplainXError(
                "Ollama returned an empty outline response.",
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
                "Ollama outline response is not valid JSON.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"error": str(exc), "preview": cleaned[:300]},
            ) from exc
        if not isinstance(data, dict) or not data:
            raise ExplainXError(
                "Ollama outline JSON root must be a non-empty object.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        return data

    def _to_outline(
        self,
        payload: dict[str, Any],
        *,
        raw: RawContent,
        target_duration_sec: int,
        total_target_words: int,
        fallback_title: str,
        fallback_language: str,
    ) -> TeachingOutline:
        # Never trust LLM numerical metadata.
        for key in (
            "total_target_words",
            "target_words",
            "estimated_words",
            "estimated_duration_sec",
            "narration",
        ):
            payload.pop(key, None)

        title = (payload.get("title") or fallback_title or "Teaching Outline")[:200]
        language = str(payload.get("language") or fallback_language or "en")
        sections_raw = payload.get("sections") or []
        if not isinstance(sections_raw, list):
            raise ExplainXError(
                "Ollama outline JSON 'sections' must be an array.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )

        try:
            sections = [
                TeachingSection.model_validate(self._normalize_section(item, index=i))
                for i, item in enumerate(sections_raw, start=1)
            ]
        except ValidationError as exc:
            raise ExplainXError(
                "Ollama outline JSON failed TeachingSection validation.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"errors": exc.errors()},
            ) from exc

        if len(sections) < OUTLINE_SECTION_MIN or len(sections) > OUTLINE_SECTION_MAX:
            raise ExplainXError(
                f"TeachingOutline must have {OUTLINE_SECTION_MIN}–{OUTLINE_SECTION_MAX} sections.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"section_count": len(sections)},
            )

        outline = TeachingOutline(
            outline_id=str(uuid.uuid4()),
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=raw.source_type,
            status="draft",
            title=title,
            language=language,
            target_duration_sec=target_duration_sec,
            total_target_words=total_target_words,
            sections=sections,
            warnings=[],
            metadata={
                "generator": "ollama_outline_v1",
                "llm": True,
                "prompt_template_version": templates.PROMPT_TEMPLATE_VERSION,
            },
            created_at=utc_now_iso(),
            schema_version=TEACHING_OUTLINE_SCHEMA_VERSION,
        )
        return apply_word_budget(outline, total_target_words=total_target_words)

    @staticmethod
    def _normalize_section(item: Any, *, index: int) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ExplainXError(
                "Outline sections must be objects.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        data = dict(item)
        data.pop("target_words", None)
        data.pop("narration", None)
        data.pop("estimated_words", None)
        data.pop("estimated_duration_sec", None)

        if "learning_objective" not in data and "objective" in data:
            data["learning_objective"] = data.pop("objective")
        if "key_concepts" not in data:
            tags = data.get("concept_tags") or data.get("concepts") or []
            if isinstance(tags, list):
                data["key_concepts"] = [str(t).strip() for t in tags if str(t).strip()]
            else:
                data["key_concepts"] = []

        concepts = [str(c).strip() for c in (data.get("key_concepts") or []) if str(c).strip()]
        if not concepts:
            concepts = [str(data.get("title") or f"Concept {index}").strip() or f"Concept {index}"]
        data["key_concepts"] = concepts

        if not data.get("id"):
            data["id"] = f"outline-{uuid.uuid4().hex[:8]}"
        if not str(data.get("title") or "").strip():
            data["title"] = f"Section {index}"
        if not str(data.get("learning_objective") or "").strip():
            data["learning_objective"] = f"Teach the ideas in section {index}."
        # Placeholder until apply_word_budget runs.
        data["target_words"] = 1
        return data
