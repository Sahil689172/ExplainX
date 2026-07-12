"""Integration tests for Phase 3.5 OllamaContentGenerator (mocked Ollama client)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.core.enums import SourceType
from app.core.errors import ExplainXError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.script.ollama.client import OllamaClient
from app.features.script.ollama.generator import OllamaContentGenerator
from app.features.script.ollama.prompt_builder import PromptBuilder
from app.features.script.ollama.response_parser import ResponseParser
from app.features.script.processors.topic_processor import TopicContentProcessor
from app.features.script.protocols import ContentGenerator
from app.features.script.schemas import ScriptConcept
from app.features.script.validator import ScriptValidator


def _valid_payload(*, title: str = "Binary Search") -> dict[str, Any]:
    return {
        "title": title,
        "language": "en",
        "full_text": (
            "Today we will learn about binary search. "
            "It finds items in sorted arrays efficiently."
        ),
        "sections": [
            {
                "id": "script-section-1",
                "order": 1,
                "title": "Introduction",
                "narration_text": (
                    "Today we will learn about binary search. "
                    "It finds items in sorted arrays efficiently."
                ),
                "estimated_duration_sec": 12.0,
                "beat_ids": ["nar-1", "nar-2"],
                "concept_ids": ["concept-1"],
                "source_section_ids": ["section-1"],
            }
        ],
        "beats": [
            {
                "id": "nar-1",
                "order": 1,
                "text": "Today we will learn about binary search.",
                "section_id": "script-section-1",
                "scene_hint": "intro",
                "approx_sec": 6.0,
                "concept_ids": ["concept-1"],
            },
            {
                "id": "nar-2",
                "order": 2,
                "text": "It finds items in sorted arrays efficiently.",
                "section_id": "script-section-1",
                "scene_hint": "section_1",
                "approx_sec": 6.0,
                "concept_ids": ["concept-1"],
            },
        ],
        "key_concepts": [{"id": "concept-1", "label": "Binary Search"}],
        "estimated_duration_sec": 12.0,
        "warnings": [],
    }


class MockOllamaClient:
    """Deterministic fake Ollama client for integration tests."""

    def __init__(
        self,
        responses: list[str] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[tuple[str, str]] = []
        self.model = "mock-qwen2.5:3b"

    def generate(self, *, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if self.error is not None:
            raise self.error
        if not self.responses:
            raise AssertionError("MockOllamaClient has no responses left")
        return self.responses.pop(0)


def test_ollama_generator_implements_protocol() -> None:
    client = MockOllamaClient([json.dumps(_valid_payload())])
    generator: ContentGenerator = OllamaContentGenerator(client)
    script = generator.generate(
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        title="Binary Search",
        language="en",
        sections=[
            RawContentSection(
                id="section-1",
                text="Binary search finds items in sorted arrays.",
                order=1,
                title="Binary Search",
            )
        ],
        concepts=[ScriptConcept(id="concept-1", label="Binary Search")],
        target_duration_sec=60,
    )
    assert script.status == "draft"
    assert script.metadata["llm"] is True
    assert script.metadata["generator"] == "ollama_content_v1"
    assert script.target_duration_sec == 60
    assert len(script.beats) == 2
    assert len(client.calls) == 1


def test_topic_processor_with_ollama_generator() -> None:
    client = MockOllamaClient([json.dumps(_valid_payload())])
    generator = OllamaContentGenerator(client)
    raw = RawContent(
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        project_id="11111111-1111-1111-1111-111111111111",
        source_type=SourceType.TOPIC,
        text="Binary search algorithms",
        sections=[
            RawContentSection(
                id="section-1",
                text="Binary search algorithms",
                order=1,
                title="Binary Search",
            )
        ],
        warnings=[],
        extraction_stats=ExtractionStats(char_count=24, word_count=3, section_count=1),
        source_path="projects/11111111-1111-1111-1111-111111111111/source/topic.txt",
        source_hash="sha256:abc",
        metadata={},
        created_at=utc_now_iso(),
    )
    script = TopicContentProcessor(generator).process(raw, target_duration_sec=60)
    ScriptValidator().validate(script, raw=raw)
    assert script.metadata["llm"] is True
    assert "topic" in client.calls[0][1].lower() or "Topic" in client.calls[0][1]


def test_response_parser_retries_once_on_invalid_json() -> None:
    bad = "not json at all"
    good = json.dumps(_valid_payload())
    client = MockOllamaClient([bad, good])
    generator = OllamaContentGenerator(client)
    script = generator.generate(
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.SCRIPT,
        title="Sorting",
        language="en",
        sections=[
            RawContentSection(
                id="s1",
                text="Hello class. We study sorting.",
                order=1,
                title="Sorting",
            )
        ],
        concepts=[],
        target_duration_sec=90,
    )
    assert script.title == "Binary Search"
    assert len(client.calls) == 2
    assert "not valid" in client.calls[1][1].lower() or "Previous response" in client.calls[1][1]


def test_response_parser_fails_after_retry() -> None:
    client = MockOllamaClient(["nope", "still nope"])
    generator = OllamaContentGenerator(client)
    with pytest.raises(ExplainXError) as exc:
        generator.generate(
            project_id="11111111-1111-1111-1111-111111111111",
            content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            source_type=SourceType.PDF,
            title="Doc",
            language="en",
            sections=[
                RawContentSection(id="p1", text="Photosynthesis text", order=1, title="P1")
            ],
            concepts=[],
            target_duration_sec=60,
        )
    assert exc.value.code == "OLLAMA_INVALID_JSON"
    assert len(client.calls) == 2


def test_prompt_builder_separates_templates() -> None:
    builder = PromptBuilder()
    sections = [
        RawContentSection(id="s1", text="Topic body", order=1, title="T"),
    ]
    topic_sys, topic_user = builder.build(
        source_type=SourceType.TOPIC,
        title="T",
        language="en",
        sections=sections,
        concepts=[],
        target_duration_sec=60,
    )
    script_sys, script_user = builder.build(
        source_type=SourceType.SCRIPT,
        title="T",
        language="en",
        sections=sections,
        concepts=[],
        target_duration_sec=60,
    )
    pdf_sys, pdf_user = builder.build(
        source_type=SourceType.PDF,
        title="T",
        language="en",
        sections=sections,
        concepts=[],
        target_duration_sec=60,
    )
    assert "educational narrator" in topic_sys.lower()
    assert "preserve the author's intent" in script_sys.lower()
    assert "extracted document text" in pdf_sys.lower() or "ONLY the extracted" in pdf_sys
    assert "Input type: topic" in topic_user
    assert "Input type: custom_script" in script_user
    assert "Input type: pdf_extracted_text" in pdf_user
    assert "metadata" not in pdf_user.lower() or "no file metadata" in pdf_user.lower()
    assert "STRICT JSON" in topic_user


def test_prompt_builder_sends_text_only_for_pdf() -> None:
    _, user = PromptBuilder().build(
        source_type=SourceType.PDF,
        title="Photosynthesis",
        language="en",
        sections=[
            RawContentSection(
                id="page-1",
                text="Chloroplasts convert light energy.",
                order=1,
                title="Page 1",
            )
        ],
        concepts=[],
        target_duration_sec=60,
    )
    assert "Chloroplasts convert light energy." in user
    assert "source_path" not in user
    assert "sha256" not in user


def test_ollama_client_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx.Client, "post", boom)
    client = OllamaClient(base_url="http://127.0.0.1:9", model="x", timeout_sec=1.0)
    with pytest.raises(ExplainXError) as exc:
        client.generate(system="s", prompt="p")
    assert exc.value.code == "OLLAMA_UNAVAILABLE"


def test_ollama_client_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(httpx.Client, "post", boom)
    client = OllamaClient(base_url="http://127.0.0.1:9", model="x", timeout_sec=1.0)
    with pytest.raises(ExplainXError) as exc:
        client.generate(system="s", prompt="p")
    assert exc.value.code == "OLLAMA_TIMEOUT"


def test_ollama_client_empty_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "   "})

    transport = httpx.MockTransport(handler)
    client = OllamaClient(
        base_url="http://ollama.test",
        model="qwen2.5:3b",
        transport=transport,
    )
    with pytest.raises(ExplainXError) as exc:
        client.generate(system="s", prompt="p")
    assert exc.value.code == "OLLAMA_EMPTY_RESPONSE"


def test_response_parser_rejects_malformed_sections() -> None:
    parser = ResponseParser()
    payload = _valid_payload()
    payload["beats"] = []  # invalid vs schema min_length via EducationalScript
    with pytest.raises(ExplainXError) as exc:
        parser.parse(
            json.dumps(payload),
            project_id="11111111-1111-1111-1111-111111111111",
            content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            source_type=SourceType.TOPIC,
            target_duration_sec=60,
            fallback_title="T",
            fallback_language="en",
        )
    assert exc.value.code == "OLLAMA_INVALID_JSON"
