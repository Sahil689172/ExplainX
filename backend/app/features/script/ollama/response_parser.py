"""Parse and validate Ollama JSON into EducationalScript (Phase 3.6)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

from pydantic import ValidationError

from app.core.enums import SourceType
from app.core.errors import ExplainXError
from app.core.timeutil import utc_now_iso
from app.features.script.durations import V1_TARGET_DURATION_SEC, estimate_scene_count
from app.features.script.metrics import count_words, enrich_script_with_metrics
from app.features.script.schemas import (
    EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
    EducationalScript,
    ScriptConcept,
    TeachingSection,
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class ResponseParser:
    """Validate LLM JSON and assemble an EducationalScript.

    Retries once via ``retry_fn`` when the first parse fails.
    """

    def parse(
        self,
        raw_text: str,
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        target_duration_sec: int,
        fallback_title: str,
        fallback_language: str,
        retry_fn: Callable[[str], str] | None = None,
    ) -> EducationalScript:
        try:
            payload = self._loads(raw_text)
            return self._to_script(
                payload,
                project_id=project_id,
                content_id=content_id,
                source_type=source_type,
                target_duration_sec=target_duration_sec,
                fallback_title=fallback_title,
                fallback_language=fallback_language,
            )
        except ExplainXError as first_error:
            if retry_fn is None:
                raise
            repaired = retry_fn(raw_text)
            try:
                payload = self._loads(repaired)
                return self._to_script(
                    payload,
                    project_id=project_id,
                    content_id=content_id,
                    source_type=source_type,
                    target_duration_sec=target_duration_sec,
                    fallback_title=fallback_title,
                    fallback_language=fallback_language,
                )
            except ExplainXError as second_error:
                raise ExplainXError(
                    "Ollama returned invalid EducationalScript JSON after one retry.",
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
                "Ollama returned an empty response.",
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
                "Ollama response is not valid JSON.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"error": str(exc), "preview": cleaned[:300]},
            ) from exc
        if not isinstance(data, dict) or not data:
            raise ExplainXError(
                "Ollama JSON root must be a non-empty object.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        return data

    def _to_script(
        self,
        payload: dict[str, Any],
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        target_duration_sec: int,
        fallback_title: str,
        fallback_language: str,
    ) -> EducationalScript:
        title = (payload.get("title") or fallback_title or "Educational Script")[:200]
        language = payload.get("language") or fallback_language or "en"
        teaching_raw = payload.get("teaching_sections") or []

        try:
            teaching_sections = [
                TeachingSection.model_validate(self._normalize_section(item))
                for item in teaching_raw
            ]
            key_concepts = [
                ScriptConcept.model_validate(item)
                for item in (payload.get("key_concepts") or [])
            ]
        except ValidationError as exc:
            raise ExplainXError(
                "Ollama JSON failed EducationalScript field validation.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"errors": exc.errors()},
            ) from exc

        if not teaching_sections:
            raise ExplainXError(
                "Ollama JSON missing teaching_sections.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )

        word_count = sum(s.estimated_words for s in teaching_sections) or sum(
            count_words(s.narration) for s in teaching_sections
        )
        duration = float(
            payload.get("estimated_duration_sec")
            if payload.get("estimated_duration_sec") is not None
            else round((word_count / 140.0) * 60.0, 1)
        )
        scene_count = int(
            payload.get("estimated_scene_count")
            if payload.get("estimated_scene_count") is not None
            else estimate_scene_count(duration)
        )
        summary = str(payload.get("summary") or "").strip() or (
            f"A 2–3 minute educational explanation of {title}."
        )
        objectives = [
            str(item).strip()
            for item in (payload.get("learning_objectives") or [])
            if str(item).strip()
        ]

        assembled = {
            "script_id": payload.get("script_id") or str(uuid.uuid4()),
            "project_id": project_id,
            "content_id": content_id,
            "source_type": source_type,
            "status": "draft",
            "title": title,
            "language": language,
            "target_duration_sec": V1_TARGET_DURATION_SEC,
            "estimated_duration_sec": duration,
            "estimated_word_count": int(payload.get("estimated_word_count") or word_count),
            "estimated_scene_count": scene_count,
            "summary": summary,
            "key_concepts": [c.model_dump(mode="json") for c in key_concepts],
            "learning_objectives": objectives,
            "teaching_sections": [s.model_dump(mode="json") for s in teaching_sections],
            "warnings": list(payload.get("warnings") or []),
            "metadata": {},
            "created_at": utc_now_iso(),
            "schema_version": EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
        }
        _ = target_duration_sec  # accepted for interface compatibility; V1 forces 150.

        try:
            script = EducationalScript.model_validate(assembled)
        except ValidationError as exc:
            raise ExplainXError(
                "Ollama JSON could not be mapped to EducationalScript.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"errors": exc.errors()},
            ) from exc
        return enrich_script_with_metrics(script)

    @staticmethod
    def _normalize_section(item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ExplainXError(
                "teaching_sections entries must be objects.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
            )
        data = dict(item)
        # Tolerate older field name from Phase 3 prompts.
        if "narration" not in data and "narration_text" in data:
            data["narration"] = data.pop("narration_text")
        narration = str(data.get("narration") or "").strip()
        data["narration"] = narration
        if "estimated_words" not in data or not data.get("estimated_words"):
            data["estimated_words"] = count_words(narration)
        if "estimated_duration_sec" not in data or data.get("estimated_duration_sec") is None:
            data["estimated_duration_sec"] = round((count_words(narration) / 140.0) * 60.0, 1)
        if "concept_tags" not in data:
            data["concept_tags"] = list(data.get("concept_ids") or [])
        if "id" not in data or not data["id"]:
            data["id"] = f"teach-{uuid.uuid4().hex[:8]}"
        if "title" not in data or not str(data.get("title") or "").strip():
            data["title"] = "Section"
        return data
