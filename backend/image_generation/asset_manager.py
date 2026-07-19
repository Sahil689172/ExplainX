"""Asset Manager — semantic cache in front of ImageGenerationService.

Does not modify OpenVINOBackend or generation internals.
On CACHE_HIT, OpenVINO is never called.

Phase 5.5: optional EducationalAssetRepository for versioned concepts.
Phase 5.4 SmartAssetLibrary remains fully functional when repository is None.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from image_generation.asset_index import AssetMetadata, _utc_now_iso
from image_generation.asset_library import SmartAssetLibrary, _backend_root
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

if TYPE_CHECKING:
    from image_generation.repository import EducationalAssetRepository


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
    concept_id: str | None = None
    version: int | None = None
    quality_score: float | None = None


class AssetManager:
    """Prompt → enhance → search library/repository → reuse or generate + save."""

    def __init__(
        self,
        generation_service: ImageGenerationService,
        *,
        library: SmartAssetLibrary | None = None,
        repository: EducationalAssetRepository | None = None,
        searcher: AssetSearcher | None = None,
        embedding_searcher: AssetSearcher | None = None,
        enhancer: PromptEnhancer | None = None,
        logger: GenerationJobLogger | None = None,
        default_style: str = "flat_vector",
        generator_label: str = "OpenVINO SD1.5",
    ) -> None:
        self._service = generation_service
        self._library = library or SmartAssetLibrary(logger=logger)
        self._repository = repository
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
    def repository(self) -> EducationalAssetRepository | None:
        return self._repository

    @property
    def stats(self) -> dict[str, Any]:
        base = self._library.index.stats.to_dict()
        if self._repository is not None:
            base["repository"] = self._repository.repository_statistics().to_dict()
        return base

    def _refresh_searcher(self) -> None:
        if isinstance(self._keyword_searcher, KeywordSearcher):
            assets = list(self._library.list_assets())
            if self._repository is not None:
                assets.extend(self._repository_as_assets())
            self._keyword_searcher.set_assets(assets)

    def _repository_as_assets(self) -> list[AssetMetadata]:
        """Project best approved versions into Phase 5.4 AssetMetadata for search."""
        assert self._repository is not None
        projected: list[AssetMetadata] = []
        for concept in self._repository.list_concepts():
            best = self._repository.get_best_version(concept.concept_id)
            if best is None:
                continue
            w, h = 512, 512
            if "x" in best.resolution:
                parts = best.resolution.lower().split("x")
                try:
                    w, h = int(parts[0]), int(parts[1])
                except ValueError:
                    pass
            projected.append(
                AssetMetadata(
                    id=best.id,
                    title=concept.title,
                    category=concept.subject,
                    keywords=list(concept.keywords) or list(best.keywords),
                    style=best.style,
                    background=best.background,
                    width=w,
                    height=h,
                    created_at=best.created_at,
                    generator=best.generator,
                    prompt=best.prompt,
                    enhanced_prompt=best.enhanced_prompt,
                    file_path=best.file_path,
                    extra={
                        "concept_id": concept.concept_id,
                        "version": best.version,
                        "quality_score": best.quality_score,
                        "source": "repository",
                    },
                )
            )
        return projected

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
        concept_id: str | None = None
        version_num: int | None = None
        quality: float | None = None

        if not force_generate:
            if self._repository is not None:
                hit_meta, match_kind, concept_id, version_num, quality = (
                    self._search_repository(title=title, prompt=prompt)
                )
            if hit_meta is None:
                hit_meta, match_kind = self._search(
                    title=title, prompt=prompt, style=style_id
                )
        lookup_ms = (time.perf_counter() - lookup_started) * 1000.0

        if hit_meta is not None:
            self._library.index.stats.record_lookup(hit=True, elapsed_ms=lookup_ms)
            self._library.index.persist()
            if self._repository is not None:
                self._repository.note_cache_hit(lookup_ms)
                cid = concept_id or hit_meta.extra.get("concept_id")
                ver = version_num or hit_meta.extra.get("version")
                if cid:
                    self._repository.record_usage(
                        str(cid), int(ver) if ver is not None else None
                    )
            path = self._resolve_path(hit_meta)
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
                file_path=path if path is not None and path.is_file() else None,
                generation_response=None,
                lookup_ms=lookup_ms,
                generation_ms=0.0,
                title=hit_meta.title,
                enhanced_prompt=hit_meta.enhanced_prompt,
                message=f"Reused asset {hit_meta.id}",
                concept_id=str(concept_id or hit_meta.extra.get("concept_id") or "")
                or None,
                version=int(version_num)
                if version_num is not None
                else hit_meta.extra.get("version"),
                quality_score=quality
                if quality is not None
                else hit_meta.extra.get("quality_score"),
            )

        self._library.index.stats.record_lookup(hit=False, elapsed_ms=lookup_ms)
        self._library.index.persist()
        if self._repository is not None:
            self._repository.note_cache_miss(lookup_ms)
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

        if self._repository is not None:
            concept = self._repository.create_concept(
                title, subject=category, keywords=keywords
            )
            version = self._repository.create_version(
                concept=concept,
                source_png=Path(response.output_path),
                title=title,
                prompt=prompt,
                enhanced_prompt=enhanced_prompt,
                subject=category,
                topic=category,
                keywords=keywords,
                generator=self._generator_label,
                style=style_id,
                width=width,
                height=height,
                generation_time_ms=generation_ms,
                auto_approve=True,
            )
            concept_id = concept.concept_id
            version_num = version.version
            quality = version.quality_score
            meta.extra["concept_id"] = concept_id
            meta.extra["version"] = version_num
            meta.extra["quality_score"] = quality

        self._refresh_searcher()
        path = self._resolve_path(meta)
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
            concept_id=concept_id,
            version=version_num,
            quality_score=quality,
        )

    def _search_repository(
        self, *, title: str, prompt: str
    ) -> tuple[AssetMetadata | None, str, str | None, int | None, float | None]:
        assert self._repository is not None
        concept = self._repository.find_concept_by_title(title)
        if concept is None:
            concept = self._repository.find_concept_by_title(prompt)
        if concept is None:
            return None, "", None, None, None
        best = self._repository.get_best_version(concept.concept_id)
        if best is None:
            return None, "", None, None, None
        path = self._repository.resolve_file(best)
        if not path.is_file():
            return None, "", None, None, None
        meta = AssetMetadata(
            id=best.id,
            title=concept.title,
            category=concept.subject,
            keywords=list(concept.keywords),
            style=best.style,
            background=best.background,
            width=512,
            height=512,
            created_at=best.created_at or _utc_now_iso(),
            generator=best.generator,
            prompt=best.prompt,
            enhanced_prompt=best.enhanced_prompt,
            file_path=best.file_path,
            extra={
                "concept_id": concept.concept_id,
                "version": best.version,
                "quality_score": best.quality_score,
                "source": "repository",
            },
        )
        return (
            meta,
            "repository_best",
            concept.concept_id,
            best.version,
            best.quality_score,
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
        for searcher in (self._embedding_searcher, self._keyword_searcher):
            hits = searcher.search(query, limit=3)
            if hits:
                best = hits[0]
                path = self._resolve_path(best.asset)
                if path is not None and path.is_file():
                    return best.asset, best.match_kind
        return None, ""

    def _resolve_path(self, meta: AssetMetadata) -> Path | None:
        if meta.extra.get("source") == "repository":
            path = Path(meta.file_path)
            if not path.is_absolute():
                path = _backend_root() / path
            return path.resolve()
        return self._library.resolve_file(meta)
