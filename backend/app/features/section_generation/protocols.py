"""SectionGenerator / SectionAssurer protocols (Phase 3.8)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.outline.schemas import TeachingOutline, TeachingSection
from app.shared.section_output import SectionOutput


@runtime_checkable
class SectionGenerator(Protocol):
    """Generate spoken narration for exactly one outline section."""

    def generate_section(
        self,
        *,
        outline: TeachingOutline,
        section: TeachingSection,
        index: int,
        previous_section_summary: str,
        next_section_title: str | None,
    ) -> SectionOutput: ...


@runtime_checkable
class SectionAssurer(Protocol):
    """Validate (and optionally repair) one generated section.

    Implemented by QualityAssuranceService — injected so
    SectionGenerationService never imports quality modules.
    """

    def assure_section(
        self,
        output: SectionOutput,
        *,
        expected: TeachingSection,
        index: int,
        previous_section_summary: str,
        next_section_title: str | None,
    ) -> SectionOutput: ...
