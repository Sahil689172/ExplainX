"""Parse and validate Ollama JSON into EducationalScript payload fields."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from pydantic import ValidationError

from app.core.enums import SourceType
from app.core.errors import ExplainXError
from app.core.timeutil import utc_now_iso
from app.features.script.schemas import (
    EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
    EducationalScript,
    ScriptBeat,
    ScriptConcept,
    ScriptSection,
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
        # If model wrapped JSON in prose, attempt to extract the outermost object.
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
        if not isinstance(data, dict):
            raise ExplainXError(
                "Ollama JSON root must be an object.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"type": type(data).__name__},
            )
        if not data:
            raise ExplainXError(
                "Ollama returned an empty JSON object.",
                code="OLLAMA_EMPTY_RESPONSE",
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
        # Server-owned fields — never trust the model for identity / linkage.
        assembled: dict[str, Any] = {
            "script_id": payload.get("script_id") or _new_uuid(),
            "project_id": project_id,
            "content_id": content_id,
            "source_type": source_type,
            "status": "draft",
            "title": (payload.get("title") or fallback_title or "Educational Script")[:200],
            "language": payload.get("language") or fallback_language or "en",
            "full_text": payload.get("full_text") or "",
            "sections": payload.get("sections") or [],
            "beats": payload.get("beats") or [],
            "key_concepts": payload.get("key_concepts") or [],
            "estimated_duration_sec": payload.get("estimated_duration_sec")
            if payload.get("estimated_duration_sec") is not None
            else float(target_duration_sec),
            "target_duration_sec": target_duration_sec,
            "warnings": list(payload.get("warnings") or []),
            "metadata": {},
            "created_at": utc_now_iso(),
            "schema_version": EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
        }

        # Normalize nested models early for clearer errors.
        try:
            assembled["sections"] = [
                ScriptSection.model_validate(item).model_dump(mode="json")
                for item in assembled["sections"]
            ]
            assembled["beats"] = [
                ScriptBeat.model_validate(item).model_dump(mode="json")
                for item in assembled["beats"]
            ]
            assembled["key_concepts"] = [
                ScriptConcept.model_validate(item).model_dump(mode="json")
                for item in assembled["key_concepts"]
            ]
        except ValidationError as exc:
            raise ExplainXError(
                "Ollama JSON failed EducationalScript field validation.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"errors": exc.errors()},
            ) from exc

        if not assembled["full_text"] and assembled["sections"]:
            assembled["full_text"] = "\n\n".join(
                s["narration_text"] for s in assembled["sections"]
            )

        try:
            return EducationalScript.model_validate(assembled)
        except ValidationError as exc:
            raise ExplainXError(
                "Ollama JSON could not be mapped to EducationalScript.",
                code="OLLAMA_INVALID_JSON",
                status_code=502,
                details={"errors": exc.errors()},
            ) from exc


def _new_uuid() -> str:
    import uuid

    return str(uuid.uuid4())
