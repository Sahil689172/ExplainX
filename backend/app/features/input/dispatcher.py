"""Route validated input requests to the correct processor."""

from __future__ import annotations

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.features.input.providers.base import BaseInputProcessor, ProcessorContext
from app.features.input.providers.pdf_processor import PDFProcessor
from app.features.input.providers.script_processor import ScriptProcessor
from app.features.input.providers.topic_processor import TopicProcessor
from app.features.input.schemas import RawContent


class InputRouter:
    """Dispatches by ``source_type`` — no AI, no pipeline side effects."""

    def __init__(
        self,
        processors: dict[SourceType, BaseInputProcessor] | None = None,
    ) -> None:
        self._processors = processors or {
            SourceType.TOPIC: TopicProcessor(),
            SourceType.PDF: PDFProcessor(),
            SourceType.SCRIPT: ScriptProcessor(),
        }

    def route(self, ctx: ProcessorContext) -> RawContent:
        processor = self._processors.get(ctx.source_type)
        if processor is None:
            raise ValidationAppError(
                f"Unsupported input type for Phase 2.1/2.2: {ctx.source_type.value}",
                code="PARSER_UNSUPPORTED_TYPE",
                details={
                    "source_type": ctx.source_type.value,
                    "supported": [t.value for t in self._processors],
                },
            )
        return processor.process(ctx)
