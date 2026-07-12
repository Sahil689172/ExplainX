"""Parse single-pass Ollama JSON into EducationalScript via TeachingOutline."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from app.core.errors import ExplainXError
from app.features.outline.schemas import TeachingOutline
from app.features.script.schemas import EducationalScript
from app.features.single_script.assembler import assemble_educational_script
from app.features.single_script.ollama import templates

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class SingleScriptResponseParser:
    def parse(
        self,
        raw_text: str,
        *,
        outline: TeachingOutline,
        retry_fn: Callable[[str], str] | None = None,
        model_name: str = "unknown",
    ) -> EducationalScript:
        try:
            payload = self._loads(raw_text)
            return self._to_script(payload, outline=outline, model_name=model_name)
        except ExplainXError as first_error:
            if retry_fn is None:
                raise
            repaired = retry_fn(raw_text)
            try:
                payload = self._loads(repaired)
                return self._to_script(payload, outline=outline, model_name=model_name)
            except ExplainXError as second_error:
                raise ExplainXError(
                    "Ollama returned invalid single-script JSON after one retry.",
                    code="OLLAMA_INVALID_JSON",
                    status_code=502,
                    details={
                        "first_error": first_error.message,
                        "second_error": second_error.message,
                        "outline_id": outline.outline_id,
                    },
                ) from second_error

    def _loads(self, raw_text: str) -> dict[str, Any]:
        if not raw_text or not raw_text.strip():
            raise ExplainXError(
                "Ollama returned an empty single-script response.",
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
                "Ollama single-script response is not valid JSON.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"error": str(exc), "preview": cleaned[:300]},
            ) from exc
        if not isinstance(data, dict) or not data:
            raise ExplainXError(
                "Ollama single-script JSON root must be a non-empty object.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        return data

    def _to_script(
        self,
        payload: dict[str, Any],
        *,
        outline: TeachingOutline,
        model_name: str,
    ) -> EducationalScript:
        for key in (
            "estimated_words",
            "estimated_duration_sec",
            "target_words",
            "word_count",
            "estimated_scene_count",
        ):
            payload.pop(key, None)

        title = str(payload.get("title") or "").strip() or outline.title
        raw_sections = payload.get("sections")
        if not isinstance(raw_sections, list) or not raw_sections:
            raise ExplainXError(
                "Ollama single-script JSON missing sections array.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"outline_id": outline.outline_id},
            )

        by_id: dict[str, dict[str, Any]] = {}
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            for key in (
                "estimated_words",
                "estimated_duration_sec",
                "target_words",
                "word_count",
            ):
                item.pop(key, None)
            sid = str(item.get("id") or "").strip()
            if sid:
                by_id[sid] = item

        expected_ids = [s.id for s in outline.sections]
        missing = [sid for sid in expected_ids if sid not in by_id]
        if missing:
            raise ExplainXError(
                "Ollama single-script JSON missing outline section ids.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"missing_section_ids": missing},
            )

        narrations: dict[str, str] = {}
        for section in outline.sections:
            item = by_id[section.id]
            narration = str(item.get("narration") or "").strip()
            if not narration:
                raise ExplainXError(
                    "Ollama single-script JSON missing narration for a section.",
                    code="OLLAMA_INVALID_JSON",
                    status_code=502,
                    details={"section_id": section.id},
                )
            narrations[section.id] = narration

        return assemble_educational_script(
            outline,
            narrations=narrations,
            title=title[:200],
            warnings=[],
            metadata={
                "generator": "ollama_single_script_v1",
                "llm": True,
                "ollama_model": model_name,
                "prompt_template_version": templates.PROMPT_TEMPLATE_VERSION,
            },
        )
