"""PDF file → RawContent via PyMuPDF4LLM (no AI / no OCR in v1)."""

from __future__ import annotations

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.features.input.pdf_extract import (
    PDF_MAX_PAGES,
    extract_pdf_markdown_sections,
    inspect_pdf,
    validate_pdf_size,
)
from app.features.input.providers.base import (
    BaseInputProcessor,
    ProcessorContext,
    sha256_bytes,
)
from app.features.input.schemas import RawContent


class PDFProcessor(BaseInputProcessor):
    source_type = SourceType.PDF

    def process(self, ctx: ProcessorContext) -> RawContent:
        if ctx.file_path is None or not ctx.file_path.is_file():
            raise ValidationAppError(
                "PDF file not found for extraction.",
                code="PARSER_FILE_NOT_FOUND",
                details={"path": str(ctx.file_path) if ctx.file_path else None},
            )

        data = ctx.file_path.read_bytes()
        validate_pdf_size(len(data))
        page_count = inspect_pdf(ctx.file_path)
        extracted = extract_pdf_markdown_sections(ctx.file_path)
        source_hash = ctx.source_hash or sha256_bytes(data)

        return self._build(
            project_id=ctx.project_id,
            sections=extracted.sections,
            warnings=extracted.warnings,
            source_path=ctx.source_path_relative,
            source_hash=source_hash,
            metadata={
                "input_kind": "pdf",
                "language_hint": ctx.language_hint,
                "original_filename": ctx.original_filename,
                "pdf_page_count": page_count,
                "pdf_max_pages": PDF_MAX_PAGES,
                "extractor": "pymupdf4llm",
            },
            page_count=page_count,
        )
