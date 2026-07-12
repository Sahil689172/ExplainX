"""PDF → EducationalScript via PyMuPDF4LLM extraction + narration generation."""

from __future__ import annotations

from pathlib import Path

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.features.input.pdf_extract import extract_pdf_markdown_sections, inspect_pdf
from app.features.input.schemas import RawContent, RawContentSection
from app.features.presentation.schemas import PresentationPlan
from app.features.script.processors.pdf_filter import filter_pdf_sections
from app.features.script.generator import PlaceholderContentGenerator
from app.features.script.processors.common import (
    improve_readability,
    resolve_concepts,
    resolve_language,
    resolve_title,
)
from app.features.script.protocols import ContentGenerator
from app.features.script.schemas import EducationalScript


class PDFContentProcessor:
    """Extract with PyMuPDF4LLM, filter noise, then generate spoken narration."""

    source_type = SourceType.PDF

    def __init__(self, generator: ContentGenerator | None = None) -> None:
        self._generator = generator or PlaceholderContentGenerator()

    def process(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        plan: PresentationPlan | None = None,
        pdf_path: Path | None = None,
    ) -> EducationalScript:
        title = resolve_title(raw, plan)
        warnings = list(raw.warnings)
        sections: list[RawContentSection]

        if pdf_path is not None and pdf_path.is_file():
            inspect_pdf(pdf_path)
            extracted = extract_pdf_markdown_sections(pdf_path)
            sections = extracted.sections
            warnings.extend(extracted.warnings)
            if extracted.page_count:
                warnings.append(f"pdf_page_count={extracted.page_count}")
        else:
            sections = [
                s.model_copy(update={"text": improve_readability(s.text)})
                for s in (raw.sections or [])
                if s.text.strip()
            ]
            if not sections and raw.text.strip():
                sections = [
                    RawContentSection(
                        id="pdf-1",
                        text=improve_readability(raw.text),
                        order=1,
                        title=title,
                    )
                ]
            if not sections:
                raise ValidationAppError(
                    "PDF produced no extractable text for narration.",
                    code="PARSER_EMPTY_CONTENT",
                    details={"project_id": raw.project_id},
                )
            warnings.append("pdf_path_missing_used_raw_content")

        before = len(sections)
        sections = filter_pdf_sections(sections)
        dropped = before - len(sections)
        if dropped:
            warnings.append(
                f"filtered_{dropped}_non_teaching_pdf_sections "
                "(references/bibliography/headers/etc.)"
            )
        if not sections:
            raise ValidationAppError(
                "PDF produced no teachable text after filtering non-content sections.",
                code="PARSER_EMPTY_CONTENT",
                details={"project_id": raw.project_id},
            )

        framed: list[RawContentSection] = []
        for index, section in enumerate(sections, start=1):
            body = improve_readability(section.text)
            framed.append(
                section.model_copy(
                    update={
                        "text": body,
                        "order": index,
                        "title": section.title or f"Section {index}",
                    }
                )
            )

        return self._generator.generate(
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=SourceType.PDF,
            title=title,
            language=resolve_language(raw, plan),
            sections=framed,
            concepts=resolve_concepts(raw, plan),
            target_duration_sec=target_duration_sec,
            warnings=warnings,
            metadata={
                "processor": "pdf_content_v1_1",
                "extractor": "pymupdf4llm",
                "used_presentation_plan": plan is not None,
                "plan_id": plan.plan_id if plan else None,
                "pdf_path": str(pdf_path) if pdf_path else None,
            },
        )
