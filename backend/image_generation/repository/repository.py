"""Educational Asset Repository — concepts, versions, quality, usage."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Sequence

from image_generation.keyword_expand import expand_keywords, normalize_token
from image_generation.logger import GenerationJobLogger, get_engine_logger
from image_generation.repository.models import (
    ASSET_KIND_IMAGE,
    ConceptRecord,
    RepositoryStatistics,
    VersionRecord,
    VersionStatus,
    new_uuid,
    slugify,
    utc_now_iso,
)
from image_generation.repository.quality import QualityEvaluator, QualityResult


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class EducationalAssetRepository:
    """Production-grade concept → version repository under ``asset_library/concepts``.

    Does not replace Phase 5.4 SmartAssetLibrary; AssetManager can use both.
    Supports future asset kinds (SVG, 3D, animation, video) via ``asset_kind``.
    """

    def __init__(
        self,
        *,
        root: Path | None = None,
        quality_evaluator: QualityEvaluator | None = None,
        logger: GenerationJobLogger | None = None,
        auto_prefer_delta: float = 1.0,
    ) -> None:
        self.root = (root or (_backend_root() / "asset_library")).resolve()
        self.concepts_dir = self.root / "concepts"
        self.pending_dir = self.root / "pending_review"
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self._quality = quality_evaluator or QualityEvaluator()
        self._logger = logger or GenerationJobLogger(
            get_engine_logger("image_generation.repository")
        )
        self._auto_prefer_delta = auto_prefer_delta
        self._cache_hits = 0
        self._cache_misses = 0
        self._lookup_ms_total = 0.0
        self._lookup_count = 0

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def create_concept(
        self,
        title: str,
        *,
        subject: str = "General",
        keywords: Sequence[str] | None = None,
    ) -> ConceptRecord:
        """Create a concept folder ``concepts/<slug>/concept.json`` if missing."""
        existing = self.find_concept_by_title(title)
        if existing is not None:
            return existing

        concept_id = new_uuid()
        slug = self._unique_slug(title)
        keys = list(keywords or expand_keywords(title))
        if normalize_token(title) not in {normalize_token(k) for k in keys}:
            keys = [normalize_token(title), *keys]
        concept = ConceptRecord(
            concept_id=concept_id,
            title=title.strip(),
            subject=subject,
            keywords=sorted({normalize_token(k) for k in keys if normalize_token(k)}),
            slug=slug,
        )
        concept_dir = self.concepts_dir / slug
        (concept_dir / "versions").mkdir(parents=True, exist_ok=True)
        self._write_concept(concept)
        self._logger.info(
            "CONCEPT_CREATED",
            concept_id=concept_id,
            title=concept.title,
            slug=slug,
        )
        return concept

    def create_version(
        self,
        *,
        concept: ConceptRecord | str,
        source_png: Path | str,
        title: str,
        prompt: str,
        enhanced_prompt: str,
        subject: str | None = None,
        topic: str = "",
        keywords: Sequence[str] | None = None,
        generator: str = "OpenVINO SD1.5",
        model_version: str = "stable-diffusion-v1-5-fp16-ov",
        style: str = "flat_vector",
        background: str = "transparent",
        width: int = 512,
        height: int = 512,
        generation_time_ms: float = 0.0,
        asset_kind: str = ASSET_KIND_IMAGE,
        auto_approve: bool = True,
    ) -> VersionRecord:
        """Add a new immutable version under the concept (never overwrite)."""
        if isinstance(concept, str):
            c = self.get_concept(concept) or self.find_concept_by_title(concept)
            if c is None:
                c = self.create_concept(concept, subject=subject or "General")
            concept = c

        source = Path(source_png)
        if not source.is_file():
            raise FileNotFoundError(f"Source image missing: {source}")

        quality = self._quality.evaluate(source)
        self._logger.info(
            "QUALITY_EVALUATED",
            concept_id=concept.concept_id,
            score=quality.score,
        )

        next_ver = concept.total_versions + 1
        version_id = new_uuid()
        ver_dir = self.concepts_dir / concept.slug / "versions" / f"v{next_ver}"
        ver_dir.mkdir(parents=True, exist_ok=True)
        dest_image = ver_dir / "image.png"
        shutil.copy2(source, dest_image)

        status = VersionStatus.APPROVED if auto_approve else VersionStatus.PENDING
        keys = list(keywords or expand_keywords([title, *concept.keywords]))
        record = VersionRecord(
            id=version_id,
            concept_id=concept.concept_id,
            version=next_ver,
            title=title.strip() or concept.title,
            subject=subject or concept.subject,
            topic=topic or concept.subject,
            keywords=sorted({normalize_token(k) for k in keys if normalize_token(k)}),
            prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            generator=generator,
            model_version=model_version,
            style=style,
            background=background,
            resolution=f"{width}x{height}",
            generation_time_ms=generation_time_ms,
            quality_score=quality.score,
            approved=auto_approve,
            preferred=False,
            status=status.value,
            times_used=0,
            last_used=None,
            created_at=utc_now_iso(),
            file_path=self._rel(dest_image),
            asset_kind=asset_kind,
            quality_details=quality.details,
        )
        (ver_dir / "metadata.json").write_text(
            json.dumps(record.to_dict(), indent=2), encoding="utf-8"
        )

        concept.total_versions = next_ver
        if auto_approve:
            concept.approved_version_count += 1
        concept.last_updated = utc_now_iso()
        self._write_concept(concept)

        self._logger.info(
            "VERSION_CREATED",
            concept_id=concept.concept_id,
            version=next_ver,
            version_id=version_id,
            quality=quality.score,
            status=status.value,
        )

        if not auto_approve:
            self._enqueue_review(concept, record)
        else:
            self._maybe_auto_prefer(concept, record)

        return record

    def approve_version(self, concept_id: str, version: int) -> VersionRecord:
        concept = self._require_concept(concept_id)
        record = self._require_version(concept, version)
        was_approved = record.approved
        record.approved = True
        record.status = VersionStatus.APPROVED.value
        self._save_version(concept, record)
        if not was_approved:
            concept.approved_version_count += 1
            concept.last_updated = utc_now_iso()
            self._write_concept(concept)
        self._remove_from_review(concept.slug, version)
        self._logger.info(
            "VERSION_APPROVED",
            concept_id=concept_id,
            version=version,
        )
        return record

    def reject_version(self, concept_id: str, version: int) -> VersionRecord:
        concept = self._require_concept(concept_id)
        record = self._require_version(concept, version)
        was_approved = record.approved
        record.approved = False
        record.preferred = False
        record.status = VersionStatus.REJECTED.value
        self._save_version(concept, record)
        if was_approved and concept.approved_version_count > 0:
            concept.approved_version_count -= 1
        if concept.preferred_version == version:
            concept.preferred_version = None
        concept.last_updated = utc_now_iso()
        self._write_concept(concept)
        self._remove_from_review(concept.slug, version)
        self._logger.info(
            "VERSION_REJECTED",
            concept_id=concept_id,
            version=version,
        )
        return record

    def set_preferred_version(self, concept_id: str, version: int) -> VersionRecord:
        concept = self._require_concept(concept_id)
        record = self._require_version(concept, version)
        if record.status == VersionStatus.REJECTED.value:
            raise ValueError("Cannot prefer a rejected version")

        for other in self.list_versions(concept_id):
            if other.preferred and other.version != version:
                other.preferred = False
                self._save_version(concept, other)

        record.preferred = True
        if not record.approved:
            record.approved = True
            record.status = VersionStatus.APPROVED.value
            concept.approved_version_count += 1
        self._save_version(concept, record)
        concept.preferred_version = version
        concept.last_updated = utc_now_iso()
        self._write_concept(concept)
        self._logger.info(
            "VERSION_PREFERRED",
            concept_id=concept_id,
            version=version,
        )
        return record

    def get_best_version(self, concept_id: str) -> VersionRecord | None:
        """Preferred version, else highest-quality approved version."""
        concept = self.get_concept(concept_id)
        if concept is None:
            return None
        versions = self.list_versions(concept_id)
        if not versions:
            return None

        if concept.preferred_version is not None:
            for v in versions:
                if (
                    v.version == concept.preferred_version
                    and v.status != VersionStatus.REJECTED.value
                ):
                    self._logger.info(
                        "BEST_VERSION_SELECTED",
                        concept_id=concept_id,
                        version=v.version,
                        reason="preferred",
                    )
                    return v

        approved = [
            v for v in versions if v.approved and v.status == VersionStatus.APPROVED.value
        ]
        pool = approved or [
            v for v in versions if v.status != VersionStatus.REJECTED.value
        ]
        if not pool:
            return None
        best = max(pool, key=lambda v: (v.quality_score, v.version))
        self._logger.info(
            "BEST_VERSION_SELECTED",
            concept_id=concept_id,
            version=best.version,
            reason="highest_quality",
            quality=best.quality_score,
        )
        return best

    def record_usage(self, concept_id: str, version: int | None = None) -> VersionRecord | None:
        concept = self.get_concept(concept_id)
        if concept is None:
            return None
        if version is None:
            best = self.get_best_version(concept_id)
            if best is None:
                return None
            version = best.version
        record = self._require_version(concept, version)
        record.times_used += 1
        record.last_used = utc_now_iso()
        self._save_version(concept, record)
        self._logger.info(
            "USAGE_UPDATED",
            concept_id=concept_id,
            version=version,
            times_used=record.times_used,
        )
        return record

    def repository_statistics(self) -> RepositoryStatistics:
        concepts = self.list_concepts()
        all_versions: list[VersionRecord] = []
        for c in concepts:
            all_versions.extend(self.list_versions(c.concept_id))

        approved = [v for v in all_versions if v.status == VersionStatus.APPROVED.value]
        rejected = [v for v in all_versions if v.status == VersionStatus.REJECTED.value]
        pending = [v for v in all_versions if v.status == VersionStatus.PENDING.value]
        qualities = [v.quality_score for v in all_versions]

        highest = max(all_versions, key=lambda v: v.quality_score) if all_versions else None
        lowest = min(all_versions, key=lambda v: v.quality_score) if all_versions else None
        most = max(all_versions, key=lambda v: v.times_used) if all_versions else None
        least = min(all_versions, key=lambda v: v.times_used) if all_versions else None

        avg_lookup = (
            self._lookup_ms_total / self._lookup_count if self._lookup_count else 0.0
        )
        return RepositoryStatistics(
            total_concepts=len(concepts),
            total_versions=len(all_versions),
            approved_assets=len(approved),
            rejected_assets=len(rejected),
            pending_review=len(pending),
            average_quality=round(sum(qualities) / len(qualities), 3) if qualities else 0.0,
            highest_quality_asset=self._label(highest),
            lowest_quality_asset=self._label(lowest),
            most_used_asset=self._label(most),
            least_used_asset=self._label(least),
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
            generations_saved=self._cache_hits,
            average_lookup_ms=round(avg_lookup, 3),
        )

    def note_cache_hit(self, lookup_ms: float = 0.0) -> None:
        self._cache_hits += 1
        self._lookup_ms_total += lookup_ms
        self._lookup_count += 1

    def note_cache_miss(self, lookup_ms: float = 0.0) -> None:
        self._cache_misses += 1
        self._lookup_ms_total += lookup_ms
        self._lookup_count += 1

    # -------------------------------------------------------------------------
    # Lookup helpers
    # -------------------------------------------------------------------------

    def get_concept(self, concept_id: str) -> ConceptRecord | None:
        for c in self.list_concepts():
            if c.concept_id == concept_id:
                return c
        return None

    def find_concept_by_title(self, title: str) -> ConceptRecord | None:
        key = normalize_token(title)
        expanded = set(expand_keywords(title))
        for c in self.list_concepts():
            if normalize_token(c.title) == key:
                return c
            if key in {normalize_token(k) for k in c.keywords}:
                return c
            if expanded & set(c.keywords):
                return c
        return None

    def list_concepts(self) -> list[ConceptRecord]:
        out: list[ConceptRecord] = []
        if not self.concepts_dir.is_dir():
            return out
        for path in sorted(self.concepts_dir.glob("*/concept.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                out.append(ConceptRecord.from_dict(data))
            except (OSError, json.JSONDecodeError, TypeError, KeyError):
                continue
        return out

    def list_versions(self, concept_id: str) -> list[VersionRecord]:
        concept = self.get_concept(concept_id)
        if concept is None:
            return []
        versions_root = self.concepts_dir / concept.slug / "versions"
        if not versions_root.is_dir():
            return []
        out: list[VersionRecord] = []
        for meta_path in sorted(versions_root.glob("v*/metadata.json")):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                out.append(VersionRecord.from_dict(data))
            except (OSError, json.JSONDecodeError, TypeError, KeyError):
                continue
        out.sort(key=lambda v: v.version)
        return out

    def resolve_file(self, version: VersionRecord) -> Path:
        path = Path(version.file_path)
        if not path.is_absolute():
            path = _backend_root() / path
        return path.resolve()

    def list_pending_review(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.pending_dir.glob("*.json")):
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return items

    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------

    def _unique_slug(self, title: str) -> str:
        base = slugify(title)
        slug = base
        n = 2
        while (self.concepts_dir / slug).exists():
            slug = f"{base}_{n}"
            n += 1
        return slug

    def _write_concept(self, concept: ConceptRecord) -> None:
        path = self.concepts_dir / concept.slug / "concept.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(concept.to_dict(), indent=2), encoding="utf-8")

    def _save_version(self, concept: ConceptRecord, record: VersionRecord) -> None:
        path = (
            self.concepts_dir
            / concept.slug
            / "versions"
            / f"v{record.version}"
            / "metadata.json"
        )
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")

    def _require_concept(self, concept_id: str) -> ConceptRecord:
        concept = self.get_concept(concept_id)
        if concept is None:
            raise KeyError(f"Unknown concept_id: {concept_id}")
        return concept

    def _require_version(self, concept: ConceptRecord, version: int) -> VersionRecord:
        for v in self.list_versions(concept.concept_id):
            if v.version == version:
                return v
        raise KeyError(f"Unknown version v{version} for {concept.concept_id}")

    def _maybe_auto_prefer(
        self, concept: ConceptRecord, record: VersionRecord
    ) -> None:
        best = None
        for v in self.list_versions(concept.concept_id):
            if v.version == record.version:
                continue
            if v.preferred or (
                v.approved and concept.preferred_version == v.version
            ):
                best = v
                break
        if best is None:
            # First approved version becomes preferred
            if concept.total_versions == 1:
                self.set_preferred_version(concept.concept_id, record.version)
            return
        if record.quality_score >= best.quality_score + self._auto_prefer_delta:
            self.set_preferred_version(concept.concept_id, record.version)

    def _enqueue_review(self, concept: ConceptRecord, record: VersionRecord) -> None:
        payload = {
            "concept_id": concept.concept_id,
            "concept_title": concept.title,
            "version": record.version,
            "version_id": record.id,
            "quality_score": record.quality_score,
            "file_path": record.file_path,
            "created_at": record.created_at,
            "actions": ["approve", "reject", "mark_preferred"],
        }
        name = f"{concept.slug}_v{record.version}.json"
        (self.pending_dir / name).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def _remove_from_review(self, slug: str, version: int) -> None:
        path = self.pending_dir / f"{slug}_v{version}.json"
        if path.is_file():
            path.unlink()

    def _rel(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(_backend_root())).replace("\\", "/")
        except ValueError:
            return str(path.resolve())

    @staticmethod
    def _label(version: VersionRecord | None) -> str | None:
        if version is None:
            return None
        return f"{version.title}#v{version.version}({version.quality_score})"
