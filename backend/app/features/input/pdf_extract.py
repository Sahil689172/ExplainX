"""PDF validation + PyMuPDF4LLM extraction helpers (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import ExplainXError, ValidationAppError
from app.features.input.schemas import RawContentSection

# Phase 3 hard limits
PDF_MAX_BYTES = 25 * 1024 * 1024
PDF_MAX_PAGES = 30
TOPIC_MIN_LEN = 3
TOPIC_MAX_LEN = 500
SCRIPT_MIN_LEN = 10
SCRIPT_MAX_LEN = 200_000


@dataclass(slots=True)
class PdfExtractionResult:
    sections: list[RawContentSection]
    page_count: int
    warnings: list[str] = field(default_factory=list)


def validate_pdf_size(size_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValidationAppError(
            "Uploaded file is empty.",
            code="VALIDATION_ERROR",
            details={"field": "file"},
        )
    if size_bytes > PDF_MAX_BYTES:
        raise ExplainXError(
            "PDF exceeds the maximum allowed size (25 MB).",
            code="UPLOAD_TOO_LARGE",
            status_code=413,
            details={"max_bytes": PDF_MAX_BYTES, "size_bytes": size_bytes},
        )


def inspect_pdf(path: Path) -> int:
    """Open PDF, reject encrypted / oversize page counts. Returns page_count."""
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise ValidationAppError(
            "PDF support requires the pymupdf package.",
            code="PARSER_UNSUPPORTED_TYPE",
            details={"dependency": "pymupdf"},
        ) from exc

    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # noqa: BLE001
        raise ValidationAppError(
            "Failed to open PDF.",
            code="PARSER_UNSUPPORTED_TYPE",
            details={"error": str(exc)},
        ) from exc

    try:
        if bool(doc.is_encrypted):
            # Try empty password; still reject if authentication is required.
            try:
                unlocked = doc.authenticate("")
            except Exception:  # noqa: BLE001
                unlocked = 0
            if not unlocked:
                raise ValidationAppError(
                    "Encrypted PDFs are not supported in v1.",
                    code="PARSER_UNSUPPORTED_TYPE",
                    details={"reason": "encrypted"},
                )

        page_count = int(doc.page_count)
        if page_count > PDF_MAX_PAGES:
            raise ValidationAppError(
                f"PDF exceeds the maximum of {PDF_MAX_PAGES} pages.",
                code="VALIDATION_ERROR",
                details={"page_count": page_count, "max_pages": PDF_MAX_PAGES},
            )
        if page_count == 0:
            raise ValidationAppError(
                "PDF has no pages.",
                code="PARSER_EMPTY_CONTENT",
                details={"page_count": 0},
            )
        return page_count
    finally:
        doc.close()


def extract_pdf_markdown_sections(path: Path) -> PdfExtractionResult:
    """Extract LLM-friendly markdown per page via PyMuPDF4LLM (no OCR in v1)."""
    page_count = inspect_pdf(path)

    try:
        import pymupdf4llm
    except ImportError as exc:  # pragma: no cover
        raise ValidationAppError(
            "PDF support requires the pymupdf4llm package.",
            code="PARSER_UNSUPPORTED_TYPE",
            details={"dependency": "pymupdf4llm"},
        ) from exc

    warnings: list[str] = []
    try:
        # Disable OCR for v1 — image-only pages must fail closed.
        chunks = pymupdf4llm.to_markdown(
            str(path),
            page_chunks=True,
            use_ocr=False,
        )
    except TypeError:
        # Older pymupdf4llm without use_ocr kwarg.
        try:
            chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True)
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                "Failed to extract PDF text with PyMuPDF4LLM.",
                code="PARSER_UNSUPPORTED_TYPE",
                details={"error": str(exc)},
            ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ValidationAppError(
            "Failed to extract PDF text with PyMuPDF4LLM.",
            code="PARSER_UNSUPPORTED_TYPE",
            details={"error": str(exc)},
        ) from exc

    if isinstance(chunks, str):
        text = chunks.strip()
        if not text:
            raise ValidationAppError(
                "PDF appears image-only or has no extractable text (OCR not enabled in v1).",
                code="PARSER_EMPTY_CONTENT",
                details={"page_count": page_count, "reason": "image_only_or_empty"},
            )
        return PdfExtractionResult(
            sections=[
                RawContentSection(id="page-1", text=text, order=1, title="Page 1")
            ],
            page_count=page_count,
            warnings=warnings,
        )

    sections: list[RawContentSection] = []
    empty_pages = 0
    for index, chunk in enumerate(chunks, start=1):
        if isinstance(chunk, dict):
            page_text = str(chunk.get("text") or "").strip()
            meta = chunk.get("metadata") or {}
            page_no = meta.get("page") or meta.get("page_number") or index
        else:
            page_text = str(chunk).strip()
            page_no = index
        if not page_text:
            empty_pages += 1
            continue
        sections.append(
            RawContentSection(
                id=f"page-{page_no}",
                text=page_text,
                order=len(sections) + 1,
                title=f"Page {page_no}",
            )
        )

    if empty_pages:
        warnings.append(
            f"{empty_pages} page(s) produced no extractable text "
            "(image-only pages are rejected when the whole PDF is empty)."
        )
    if not sections:
        raise ValidationAppError(
            "PDF appears image-only or has no extractable text (OCR not enabled in v1).",
            code="PARSER_EMPTY_CONTENT",
            details={"page_count": page_count, "reason": "image_only_or_empty"},
        )

    return PdfExtractionResult(
        sections=sections,
        page_count=page_count,
        warnings=warnings,
    )
