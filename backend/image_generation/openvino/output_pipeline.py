"""Post-generation output pipeline: Asset Processor → Asset Library."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from image_generation.logger import GenerationJobLogger
from image_generation.models import GenerationJob, GenerationRequest


@runtime_checkable
class OutputPipelineProtocol(Protocol):
    """Optional post-processor hooked into ImageGenerationService (DI)."""

    def process(
        self,
        *,
        raw_png: str,
        request: GenerationRequest,
        job: GenerationJob,
    ) -> str:
        """Return final asset path (processed). May register library entries."""
        ...


class AssetOutputPipeline:
    """Temp PNG → AssetProcessor → AssetLibrary → processed path."""

    def __init__(
        self,
        *,
        asset_processor: object | None = None,
        asset_library: object | None = None,
        logger: GenerationJobLogger | None = None,
        use_stub_remover: bool | None = None,
    ) -> None:
        self._processor = asset_processor
        self._library = asset_library
        self._logger = logger or GenerationJobLogger()
        if use_stub_remover is None:
            use_stub_remover = os.environ.get(
                "EXPLAINX_OPEN_VINO_STUB", ""
            ).strip() in {"1", "true", "True"}
        self._use_stub_remover = bool(use_stub_remover)

    def process(
        self,
        *,
        raw_png: str,
        request: GenerationRequest,
        job: GenerationJob,
    ) -> str:
        raw_path = Path(raw_png)
        if not raw_path.is_file():
            raise FileNotFoundError(f"Raw PNG missing: {raw_png}")

        processor = self._processor or self._default_processor()
        processed = processor.process(raw_path)
        processed_path = Path(processed.processed_path)
        digest = getattr(processed.metadata, "hash", None) or self._file_hash(
            processed_path
        )

        library = self._library
        if library is not None:
            record = self._to_record(request, processed_path, digest, job.job_id)
            registered = library.register(record)
            job.metadata.set("asset_id", str(registered.asset_id))
            job.metadata.set("asset_hash", digest)
            self._logger.info(
                "ASSET_LIBRARY_REGISTER",
                asset_id=str(registered.asset_id),
                path=str(processed_path),
            )

        job.metadata.set("processed_path", str(processed_path))
        job.metadata.set(
            "asset_metadata",
            processed.metadata.to_dict()
            if hasattr(processed.metadata, "to_dict")
            else {},
        )
        self._logger.info("ASSET_PROCESSOR_DONE", path=str(processed_path))
        return str(processed_path)

    def _default_processor(self) -> object:
        from asset_processor import AssetProcessor, AssetProcessorConfig

        return AssetProcessor(
            AssetProcessorConfig(use_stub_remover=self._use_stub_remover)
        )

    @staticmethod
    def _file_hash(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    @staticmethod
    def _to_record(
        request: GenerationRequest,
        processed_path: Path,
        digest: str,
        job_id: UUID,
    ) -> object:
        from asset_intelligence.schemas.asset import (
            AssetCategory,
            AssetOntologyEntry,
            AssetRecord,
            AssetScope,
        )

        name = request.asset_semantic_name or "generated_asset"
        return AssetRecord(
            semantic_name=name,
            ontology=AssetOntologyEntry(
                concept=name,
                category=AssetCategory.OTHER,
                tags=["generated", "openvino", request.style_id],
                style_id=request.style_id,
                subject=request.project_id,
            ),
            scope=AssetScope.PROJECT if request.project_id else AssetScope.GLOBAL,
            content_hash=digest,
            style_id=request.style_id,
            file_path=str(processed_path),
            processed_path=str(processed_path),
            metadata={
                "job_id": str(job_id),
                "request_id": str(request.request_id),
                "prompt_preview": request.prompt[:120],
                "source": "openvino",
            },
        )
