"""Per-section narration output schemas (Phase 3.8).

Canonical model lives in ``app.shared.section_output`` so quality repair
can depend on it without importing the section_generation package.
"""

from __future__ import annotations

from app.shared.section_output import (
    SECTION_OUTPUT_SCHEMA_VERSION,
    SectionOutput,
)

__all__ = [
    "SECTION_OUTPUT_SCHEMA_VERSION",
    "SectionOutput",
]
