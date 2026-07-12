"""Input-specific EducationalScript processors (Phase 3)."""

from app.features.script.processors.pdf_processor import PDFContentProcessor
from app.features.script.processors.script_processor import ScriptContentProcessor
from app.features.script.processors.topic_processor import TopicContentProcessor

__all__ = [
    "PDFContentProcessor",
    "ScriptContentProcessor",
    "TopicContentProcessor",
]
