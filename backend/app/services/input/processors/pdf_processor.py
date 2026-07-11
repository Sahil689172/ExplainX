"""PDF file → RawContent via local text extraction (no AI / no OCR)."""

from __future__ import annotations

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.models.artifacts.raw_content import RawContent, RawContentSection
from app.services.input.processors.base import (
    BaseInputProcessor,
    ProcessorContext,
    sha256_bytes,
)


class PDFProcessor(BaseInputProcessor):
    source_type = SourceType.PDF

    def process(self, ctx: ProcessorContext) -> RawContent:
        if ctx.file_path is None or not ctx.file_path.is_file():
            raise ValidationAppError(
                "PDF file not found for extraction.",
                code="PARSER_FILE_NOT_FOUND",
                details={"path": str(ctx.file_path) if ctx.file_path else None},
            )

        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise ValidationAppError(
                "PDF support requires the pypdf package.",
                code="PARSER_UNSUPPORTED_TYPE",
                details={"dependency": "pypdf"},
            ) from exc

        try:
            reader = PdfReader(str(ctx.file_path))
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                "Failed to open PDF.",
                code="PARSER_UNSUPPORTED_TYPE",
                details={"error": str(exc)},
            ) from exc

        if getattr(reader, "is_encrypted", False):
            try:
                unlocked = reader.decrypt("")  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                unlocked = 0
            if not unlocked:
                raise ValidationAppError(
                    "Encrypted PDFs are not supported without a password.",
                    code="PARSER_UNSUPPORTED_TYPE",
                    details={"reason": "encrypted"},
                )

        warnings: list[str] = []
        sections: list[RawContentSection] = []
        empty_pages = 0

        for index, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"page_{index}_extract_failed: {exc}")
                page_text = ""
            cleaned = page_text.strip()
            if not cleaned:
                empty_pages += 1
                continue
            sections.append(
                RawContentSection(
                    id=f"page-{index}",
                    text=cleaned,
                    order=len(sections) + 1,
                    title=f"Page {index}",
                )
            )

        page_count = len(reader.pages)
        if empty_pages:
            warnings.append(
                f"{empty_pages} page(s) produced no extractable text "
                "(scanned PDFs need OCR in a later phase)."
            )
        if not sections:
            raise ValidationAppError(
                "PDF produced no extractable text.",
                code="PARSER_EMPTY_CONTENT",
                details={"page_count": page_count, "warnings": warnings},
            )

        data = ctx.file_path.read_bytes()
        source_hash = ctx.source_hash or sha256_bytes(data)

        return self._build(
            project_id=ctx.project_id,
            sections=sections,
            warnings=warnings,
            source_path=ctx.source_path_relative,
            source_hash=source_hash,
            metadata={
                "input_kind": "pdf",
                "language_hint": ctx.language_hint,
                "original_filename": ctx.original_filename,
                "pdf_page_count": page_count,
            },
            page_count=page_count,
        )
