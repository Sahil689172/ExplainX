"""Filter non-teaching PDF noise before narration generation (Phase 3.6)."""

from __future__ import annotations

import re

from app.features.input.schemas import RawContentSection

_IGNORE_HEADING = re.compile(
    r"^\s*("
    r"references?|bibliography|acknowledgements?|acknowledgments?|"
    r"index(?:es)?|appendices|appendix|contents|table of contents|"
    r"works cited|further reading"
    r")\s*$",
    re.IGNORECASE,
)

_REPEATED_LINE = re.compile(r"^\s*(page\s+\d+|\d+\s*/\s*\d+)\s*$", re.IGNORECASE)


def is_noise_section(section: RawContentSection) -> bool:
    title = (section.title or "").strip()
    if title and _IGNORE_HEADING.match(title):
        return True
    text = section.text.strip()
    if not text:
        return True
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line and _IGNORE_HEADING.match(first_line):
        return True
    # Very short page markers / headers.
    if len(text) < 40 and _REPEATED_LINE.match(text):
        return True
    return False


def filter_pdf_sections(sections: list[RawContentSection]) -> list[RawContentSection]:
    """Drop references/bibliography/etc. and renumber remaining sections."""
    kept = [s for s in sections if not is_noise_section(s)]
    cleaned: list[RawContentSection] = []
    for index, section in enumerate(kept, start=1):
        cleaned.append(section.model_copy(update={"order": index}))
    return cleaned
