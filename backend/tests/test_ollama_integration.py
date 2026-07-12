"""Integration tests for OllamaContentGenerator with Phase 3.6 schema (mocked)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.core.enums import SourceType
from app.core.errors import ExplainXError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.script.durations import V1_TARGET_DURATION_SEC
from app.features.script.ollama.client import OllamaClient
from app.features.script.ollama.generator import OllamaContentGenerator
from app.features.script.ollama.prompt_builder import PromptBuilder
from app.features.script.ollama.response_parser import ResponseParser
from app.features.script.processors.topic_processor import TopicContentProcessor
from app.features.script.protocols import ContentGenerator
from app.features.script.schemas import ScriptConcept
from app.features.script.validator import ScriptValidator


def _words(n: int, seed: str = "learning") -> str:
    return " ".join(f"{seed}{i}" for i in range(n))


def _valid_payload(*, title: str = "Binary Search") -> dict[str, Any]:
    # ~360 words across sections → ~154s at 140 WPM (inside 120–180 / 300–450).
    sections = []
    for i in range(6):
        narration = _words(60, seed=f"section{i}word")
        sections.append(
            {
                "id": f"teach-{i+1}",
                "title": f"Section {i+1}",
                "narration": narration + ".",
                "estimated_duration_sec": round(60 / 140 * 60, 1),
                "estimated_words": 60,
                "concept_tags": ["Binary Search"],
            }
        )
    return {
        "title": title,
        "language": "en",
        "summary": f"A 2–3 minute explanation of {title}.",
        "key_concepts": [{"id": "concept-1", "label": "Binary Search"}],
        "learning_objectives": [
            "Explain binary search",
            "Apply binary search to a sorted list",
        ],
        "teaching_sections": sections,
        "estimated_duration_sec": 154.0,
        "estimated_word_count": 360,
        "estimated_scene_count": 20,
        "warnings": [],
    }


class MockOllamaClient:
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
    assert script.target_duration_sec == V1_TARGET_DURATION_SEC
    assert len(script.teaching_sections) == 6
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
    script = TopicContentProcessor(generator).process(raw, target_duration_sec=150)
    ScriptValidator().validate(script, raw=raw)
    assert script.metadata["llm"] is True


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
        target_duration_sec=150,
    )
    assert script.title == "Binary Search"
    assert len(client.calls) == 2


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
            target_duration_sec=150,
        )
    assert exc.value.code == "OLLAMA_INVALID_JSON"
    assert len(client.calls) == 2


def test_prompt_builder_v1_templates() -> None:
    builder = PromptBuilder()
    sections = [RawContentSection(id="s1", text="Topic body", order=1, title="T")]
    topic_sys, topic_user = builder.build(
        source_type=SourceType.TOPIC,
        title="T",
        language="en",
        sections=sections,
        concepts=[],
        target_duration_sec=150,
    )
    assert "2–3 minute" in topic_sys or "2-3 minute" in topic_sys.replace("–", "-")
    assert "teaching_sections" in topic_user
    assert "STRICT JSON" in topic_user


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


def test_response_parser_rejects_empty_teaching_sections() -> None:
    parser = ResponseParser()
    payload = _valid_payload()
    payload["teaching_sections"] = []
    with pytest.raises(ExplainXError) as exc:
        parser.parse(
            json.dumps(payload),
            project_id="11111111-1111-1111-1111-111111111111",
            content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            source_type=SourceType.TOPIC,
            target_duration_sec=150,
            fallback_title="T",
            fallback_language="en",
        )
    assert exc.value.code == "OLLAMA_INVALID_JSON"
