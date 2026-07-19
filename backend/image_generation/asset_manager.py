"""Asset Manager — semantic cache in front of ImageGenerationService.

Does not modify OpenVINOBackend or generation internals.
On CACHE_HIT, OpenVINO is never called.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from image_generation.asset_index import AssetMetadata
from image_generation.asset_library import SmartAssetLibrary
from image_generation.asset_search import (
    AssetSearcher,
    EmbeddingSearcher,
    KeywordSearcher,
    SearchQuery,
)
from image_generation.image_generation_service import ImageGenerationService
from image_generation.keyword_expand import expand_from_prompt
from image_generation.logger import GenerationJobLogger, get_engine_logger
from image_generation.models import (
    GenerationMetadata,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    OutputFormat,
)
from image_generation.prompt_enhancer import PromptEnhancer


@dataclass(slots=True)
class AssetResolveResult:
    """Outcome of ``AssetManager.resolve``."""

    cache_hit: bool
    asset: AssetMetadata | None
    file_path: Path | None
    generation_response: GenerationResponse | None
    lookup_ms: float
    generation_ms: float | None
    title: str
    enhanced_prompt: str
    message: str


class AssetManager:
    """Prompt → enhance → search library → reuse or generate + save."""

    def __init__(
        self,
        generation_service: ImageGenerationService,
        *,
        library: SmartAssetLibrary | None = None,
        searcher: AssetSearcher | None = None,
        embedding_searcher: AssetSearcher | None = None,
        enhancer: PromptEnhancer | None = None,
        logger: GenerationJobLogger | None = None,
        default_style: str = "flat_vector",
        generator_label: str = "OpenVINO SD1.5",
    ) -> None:
        self._service = generation_service
        self._library = library or SmartAssetLibrary(logger=logger)
        self._keyword_searcher = searcher or KeywordSearcher()
        self._embedding_searcher = embedding_searcher or EmbeddingSearcher()
        self._enhancer = enhancer or PromptEnhancer()
        self._logger = logger or GenerationJobLogger(
            get_engine_logger("image_generation.asset_manager")
        )
        self._default_style = default_style
        self._generator_label = generator_label
        self._refresh_searcher()

    @property
    def library(self) -> SmartAssetLibrary:
        return self._library

    @property
    def stats(self) -> dict[str, Any]:
        return self._library.index.stats.to_dict()

    def _refresh_searcher(self) -> None:
        if isinstance(self._keyword_searcher, KeywordSearcher):
            self._keyword_searcher.set_assets(self._library.list_assets())

    def resolve(
        self,
        prompt: str,
        *,
        style: str | None = None,
        force_generate: bool = False,
        width: int = 512,
        height: int = 512,
    ) -> AssetResolveResult:
        style_id = style or self._default_style
        enhanced = self._enhancer.enhance(prompt, style=style_id)
        title = enhanced["title"]
        enhanced_prompt = enhanced["enhanced_prompt"]
        category = enhanced["category"]
        keywords = expand_from_prompt(prompt, title=title)

        lookup_started = time.perf_counter()
        hit_meta: AssetMetadata | None = None
        match_kind = ""

        if not force_generate:
            hit_meta, match_kind = self._search(title=title, prompt=prompt, style=style_id)
        lookup_ms = (time.perf_counter() - lookup_started) * 1000.0

        if hit_meta is not None:
            self._library.index.stats.record_lookup(hit=True, elapsed_ms=lookup_ms)
            self._library.index.persist()
            path = self._library.resolve_file(hit_meta)
            self._logger.info(
                "CACHE_HIT",
                asset_id=hit_meta.id,
                title=hit_meta.title,
                match=match_kind,
                lookup_ms=round(lookup_ms, 3),
            )
            print("CACHE HIT", flush=True)
            return AssetResolveResult(
                cache_hit=True,
                asset=hit_meta,
                file_path=path if path.is_file() else None,
                generation_response=None,
                lookup_ms=lookup_ms,
                generation_ms=0.0,
                title=hit_meta.title,
                enhanced_prompt=hit_meta.enhanced_prompt,
                message=f"Reused asset {hit_meta.id}",
            )

        self._library.index.stats.record_lookup(hit=False, elapsed_ms=lookup_ms)
        self._library.index.persist()
        self._logger.info(
            "CACHE_MISS",
            title=title,
            lookup_ms=round(lookup_ms, 3),
        )
        print("CACHE MISS", flush=True)

        gen_started = time.perf_counter()
        engine_style = "flat"
        if style_id.split("_")[0] in self._service.config.supported_styles:
            engine_style = style_id.split("_")[0]
        elif style_id in self._service.config.supported_styles:
            engine_style = style_id

        request = GenerationRequest(
            prompt=enhanced_prompt,
            style_id=engine_style,
            width=width,
            height=height,
            aspect_ratio="1:1",
            output_format=OutputFormat.PNG,
            asset_semantic_name=title.replace(" ", "_"),
            backend_id="openvino",
            metadata=GenerationMetadata(
                entries={
                    "title": title,
                    "enhanced_prompt": enhanced_prompt,
                    "original_prompt": prompt,
                }
            ),
        )

        response = self._service.generate(request)
        generation_ms = (time.perf_counter() - gen_started) * 1000.0

        if response.status != GenerationStatus.COMPLETED or not response.output_path:
            return AssetResolveResult(
                cache_hit=False,
                asset=None,
                file_path=None,
                generation_response=response,
                lookup_ms=lookup_ms,
                generation_ms=generation_ms,
                title=title,
                enhanced_prompt=enhanced_prompt,
                message=response.error or "Generation failed",
            )

        meta = self._library.save_new_asset(
            source_png=Path(response.output_path),
            title=title,
            prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            style=style_id,
            category=category,
            background="transparent",
            width=width,
            height=height,
            generator=self._generator_label,
            keywords=keywords,
        )
        self._refresh_searcher()
        path = self._library.resolve_file(meta)
        return AssetResolveResult(
            cache_hit=False,
            asset=meta,
            file_path=path,
            generation_response=response,
            lookup_ms=lookup_ms,
            generation_ms=generation_ms,
            title=title,
            enhanced_prompt=enhanced_prompt,
            message=f"Generated and saved asset {meta.id}",
        )

    def _search(
        self, *, title: str, prompt: str, style: str
    ) -> tuple[AssetMetadata | None, str]:
        self._refresh_searcher()
        query = SearchQuery(
            text=prompt,
            title=title,
            keywords=expand_from_prompt(prompt, title=title),
            style=style,
        )
        # Embedding placeholder first (empty today), then keywords.
        for searcher in (self._embedding_searcher, self._keyword_searcher):
            hits = searcher.search(query, limit=3)
            if hits:
                best = hits[0]
                path = self._library.resolve_file(best.asset)
                if path.is_file():
                    return best.asset, best.match_kind
        return None, ""
