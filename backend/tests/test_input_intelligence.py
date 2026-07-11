"""Unit + API tests for Phase 2.1 / 2.2 Input Intelligence."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.models.api.inputs import ScriptSourceRequest, TopicSourceRequest
from app.services.input.input_router import InputRouter
from app.services.input.processors.base import ProcessorContext
from app.services.input.processors.pdf_processor import PDFProcessor
from app.services.input.processors.script_processor import ScriptProcessor
from app.services.input.processors.topic_processor import TopicProcessor


def _minimal_pdf_bytes(text: str) -> bytes:
    """Build a tiny PDF containing ``text`` as an extractable text object."""
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
        (
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        ),
    ]
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode("latin-1", errors="replace")
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    xref_positions = [0]
    for obj in objects:
        xref_positions.append(len(out))
        out.extend(obj)
    xref_start = len(out)
    out.extend(f"xref\n0 {len(xref_positions)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for pos in xref_positions[1:]:
        out.extend(f"{pos:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(xref_positions)} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n".encode()
    )
    return bytes(out)


def _make_text_pdf(path: Path, text: str) -> Path:
    path.write_bytes(_minimal_pdf_bytes(text))
    return path


def _create_project(client: TestClient, title: str = "Input Test") -> str:
    response = client.post(
        "/api/v1/projects",
        json={
            "title": title,
            "source_type": "topic",
            "source_topic": "placeholder topic for create",
            "theme_id": "notebooklm",
            "source_language_code": "en",
            "target_language_code": "en",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["project_id"]


def test_topic_processor_unified_schema() -> None:
    raw = TopicProcessor().process(
        ProcessorContext(
            project_id="11111111-1111-1111-1111-111111111111",
            source_type=SourceType.TOPIC,
            topic="Binary search algorithms",
        )
    )
    assert raw.source_type == SourceType.TOPIC
    assert raw.text == "Binary search algorithms"
    assert len(raw.sections) == 1
    assert raw.extraction_stats.char_count == len(raw.text)
    assert raw.warnings == []


def test_script_processor_splits_paragraphs() -> None:
    script = "First paragraph about trees.\n\nSecond paragraph about recursion."
    raw = ScriptProcessor().process(
        ProcessorContext(
            project_id="11111111-1111-1111-1111-111111111111",
            source_type=SourceType.SCRIPT,
            script_text=script,
            extra={"title": "Trees"},
        )
    )
    assert raw.source_type == SourceType.SCRIPT
    assert len(raw.sections) == 2
    assert "First paragraph" in raw.text
    assert raw.sections[0].title == "Trees"


def test_pdf_processor_extracts_text(tmp_path: Path) -> None:
    pdf_path = _make_text_pdf(tmp_path / "lesson.pdf", "Hello ExplainX PDF extraction")
    raw = PDFProcessor().process(
        ProcessorContext(
            project_id="11111111-1111-1111-1111-111111111111",
            source_type=SourceType.PDF,
            file_path=pdf_path,
            original_filename="lesson.pdf",
        )
    )
    assert raw.source_type == SourceType.PDF
    assert "Hello ExplainX" in raw.text
    assert raw.extraction_stats.section_count >= 1
    assert raw.source_hash.startswith("sha256:")


def test_pdf_processor_empty_raises(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    blank = tmp_path / "blank.pdf"
    with blank.open("wb") as handle:
        writer.write(handle)
    with pytest.raises(ValidationAppError) as exc:
        PDFProcessor().process(
            ProcessorContext(
                project_id="11111111-1111-1111-1111-111111111111",
                source_type=SourceType.PDF,
                file_path=blank,
            )
        )
    assert exc.value.code == "PARSER_EMPTY_CONTENT"


def test_input_router_dispatches() -> None:
    router = InputRouter()
    topic = router.route(
        ProcessorContext(
            project_id="11111111-1111-1111-1111-111111111111",
            source_type=SourceType.TOPIC,
            topic="Photosynthesis basics",
        )
    )
    assert topic.source_type == SourceType.TOPIC
    with pytest.raises(ValidationAppError) as exc:
        router.route(
            ProcessorContext(
                project_id="11111111-1111-1111-1111-111111111111",
                source_type=SourceType.DOCX,
            )
        )
    assert exc.value.code == "PARSER_UNSUPPORTED_TYPE"


def test_api_topic_ingest_and_get(client: TestClient, _test_env: Path) -> None:
    project_id = _create_project(client, title="Topic Ingest")
    response = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Binary search for beginners", "replace": False},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["source_type"] == "topic"
    assert body["raw_content"]["source_type"] == "topic"
    assert body["raw_content"]["text"] == "Binary search for beginners"

    artifact = _test_env / "projects" / project_id / "artifacts" / "v1" / "raw_content.json"
    assert artifact.is_file()

    got = client.get(f"/api/v1/projects/{project_id}/raw-content")
    assert got.status_code == 200
    assert got.json()["data"]["content_id"] == body["raw_content"]["content_id"]

    conflict = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Another topic here", "replace": False},
    )
    assert conflict.status_code == 409


def test_api_script_ingest(client: TestClient) -> None:
    project_id = _create_project(client, title="Script Ingest")
    response = client.put(
        f"/api/v1/projects/{project_id}/source/script",
        json={
            "script": "Welcome to the lesson.\n\nToday we learn sorting.",
            "title": "Sorting 101",
            "replace": True,
        },
    )
    assert response.status_code == 200, response.text
    raw = response.json()["data"]["raw_content"]
    assert raw["source_type"] == "script"
    assert len(raw["sections"]) == 2


def test_api_pdf_upload(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, title="PDF Ingest")
    pdf_path = _make_text_pdf(tmp_path / "upload.pdf", "Uploaded PDF body for ExplainX")
    with pdf_path.open("rb") as handle:
        response = client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("upload.pdf", handle, "application/pdf")},
            data={"replace": "true"},
        )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["source_type"] == "pdf"
    assert "Uploaded PDF body" in data["raw_content"]["text"]
    assert data["raw_content"]["source_type"] == "pdf"


def test_api_rejects_non_pdf(client: TestClient) -> None:
    project_id = _create_project(client, title="Bad Upload")
    response = client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("notes.txt", BytesIO(b"hello world text"), "text/plain")},
        data={"replace": "true"},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_SOURCE_TYPE"


def test_request_models_validate() -> None:
    TopicSourceRequest(topic="Valid topic string")
    with pytest.raises(Exception):
        TopicSourceRequest(topic="ab")
    ScriptSourceRequest(script="Long enough custom script text")
    with pytest.raises(Exception):
        ScriptSourceRequest(script="short")
