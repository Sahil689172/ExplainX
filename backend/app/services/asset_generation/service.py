"""AssetGenerationService — ScenePlan → deterministic GeneratedAsset bundle."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.errors import ValidationAppError
from app.services.asset_generation.cache import AssetGenerationCache, compute_plan_hash
from app.services.asset_generation.exporter import AssetExporter
from app.services.asset_generation.models import (
    AssetBundle,
    AssetStatus,
    GenerationResult,
    ScenePackage,
)
from app.services.asset_generation.registry import GeneratorRegistry, default_registry
from app.services.asset_generation.scene_composer import SceneComposer
from app.services.asset_generation.validator import AssetValidator

logger = logging.getLogger("explainx.asset_generation")


@dataclass
class AssetGenerationService:
    """Orchestrate generator selection, cache, validation, export, and composition."""

    registry: GeneratorRegistry = field(default_factory=default_registry)
    cache: AssetGenerationCache | None = None
    validator: AssetValidator = field(default_factory=AssetValidator)
    exporter: AssetExporter = field(default_factory=AssetExporter)
    composer: SceneComposer = field(default_factory=SceneComposer)
    style: str = "educational"
    theme: str = "light"
    language: str = "en"

    @classmethod
    def with_cache(
        cls,
        cache_dir: str | Path,
        **kwargs: Any,
    ) -> AssetGenerationService:
        return cls(cache=AssetGenerationCache(cache_dir), **kwargs)

    def generate(
        self,
        plan: Any,
        *,
        output_dir: str | Path,
        export_dir: str | Path | None = None,
        compose: bool = True,
    ) -> AssetBundle:
        """Generate assets for one ScenePlan.

        ``plan`` is a Visual Intelligence :class:`ScenePlan` (duck-typed to avoid
        hard coupling beyond imports used at call sites).
        """
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        work = output / plan.scene_id
        work.mkdir(parents=True, exist_ok=True)

        digest = self._hash_plan(plan)
        if self.cache is not None:
            cached = self.cache.lookup(digest)
            if cached is not None:
                assets, metadata = cached
                result = GenerationResult(
                    scene_id=plan.scene_id,
                    generator=metadata.generator,
                    status=AssetStatus.CACHED,
                    assets=assets,
                    primary_path=next(
                        (a.path for a in assets if a.path.endswith(".png")),
                        assets[0].path if assets else None,
                    ),
                    content_hash=digest,
                    cache_hit=True,
                    generation_time_sec=0.0,
                    detail="cache hit",
                    metadata=metadata,
                )
                logger.info(
                    "asset cache hit scene=%s generator=%s hash=%s",
                    plan.scene_id,
                    metadata.generator.value,
                    digest[:16],
                )
                return self._finalize(result, export_dir or output, compose=compose)

        result = self._generate_fresh(plan, work, digest)
        result = self.validator.validate_result(result)

        if self.cache is not None and result.metadata is not None:
            stored = self.cache.store(digest, assets=result.assets, metadata=result.metadata)
            result = result.model_copy(
                update={
                    "assets": stored,
                    "content_hash": digest,
                    "primary_path": next(
                        (a.path for a in stored if a.path.endswith(".png")),
                        result.primary_path,
                    ),
                }
            )

        return self._finalize(result, export_dir or output, compose=compose)

    def generate_many(
        self,
        plans: list[Any],
        *,
        output_dir: str | Path,
        export_dir: str | Path | None = None,
        compose: bool = True,
    ) -> list[AssetBundle]:
        return [
            self.generate(p, output_dir=output_dir, export_dir=export_dir, compose=compose)
            for p in plans
        ]

    def compose_bundle(self, bundle: AssetBundle) -> ScenePackage:
        return self.composer.compose(bundle)

    # ---- internals ------------------------------------------------------- #

    def _generate_fresh(self, plan: Any, work: Path, digest: str) -> GenerationResult:
        candidates = self.registry.candidates(plan)
        preferred = self.registry.select(plan)
        ordered = []
        if preferred is not None:
            ordered.append(preferred)
        for gen in candidates:
            if preferred is None or gen.generator_type() != preferred.generator_type():
                ordered.append(gen)

        if not ordered:
            raise ValidationAppError(
                "No registered generator supports this ScenePlan.",
                code="ASSET_NO_GENERATOR",
                details={
                    "scene_id": plan.scene_id,
                    "visual_type": plan.intent.visual_type.value,
                    "renderer": plan.strategy.primary_renderer.value,
                },
            )

        errors: list[str] = []
        for gen in ordered:
            if gen.generator_type().value == "local_image":
                # Interface-only — never call for real generation in this phase.
                continue
            started = time.perf_counter()
            result = gen.generate(plan, work)
            result = result.model_copy(
                update={
                    "content_hash": digest,
                    "generation_time_sec": result.generation_time_sec
                    or round(time.perf_counter() - started, 4),
                }
            )
            if result.status in {AssetStatus.SKIPPED, AssetStatus.FAILED}:
                errors.append(result.detail or result.status.value)
                continue
            if result.metadata is not None:
                result = result.model_copy(
                    update={
                        "metadata": result.metadata.model_copy(
                            update={"content_hash": digest}
                        )
                    }
                )
            logger.info(
                "asset generated scene=%s generator=%s time=%.3fs hash=%s",
                plan.scene_id,
                gen.generator_type().value,
                result.generation_time_sec,
                digest[:16],
            )
            return result

        raise ValidationAppError(
            "All candidate generators failed or were skipped.",
            code="ASSET_GENERATION_FAILED",
            details={"scene_id": plan.scene_id, "errors": errors},
        )

    def _finalize(
        self, result: GenerationResult, export_dir: Path | str, *, compose: bool
    ) -> AssetBundle:
        bundle = self.exporter.export(result, export_dir)
        if compose:
            package = self.composer.compose(bundle)
            bundle = bundle.model_copy(update={"composed_path": package.composed_path})
        return bundle

    def _hash_plan(self, plan: Any) -> str:
        return compute_plan_hash(
            scene_id=plan.scene_id,
            visual_type=plan.intent.visual_type.value,
            renderer=plan.strategy.primary_renderer.value,
            style=self.style,
            theme=self.theme,
            language=self.language,
            title=plan.intent.reasoning[:80],
            narration="",
            keywords=list(plan.intent.matched_keywords or []),
            extra={"complexity": plan.intent.complexity.value},
        )
