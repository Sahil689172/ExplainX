"""Asset processing pipeline — official gateway for ExplainX image assets."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from PIL import Image

from asset_processor.asset_cache import AssetCache
from asset_processor.asset_validator import AssetValidator
from asset_processor.background_remover import BackgroundRemover
from asset_processor.config import SUPPORTED_EXTENSIONS, AssetProcessorConfig
from asset_processor.exceptions import AssetProcessorError, ImageLoadError
from asset_processor.image_normalizer import ImageNormalizer
from asset_processor.image_resizer import ImageResizer
from asset_processor.metadata_generator import MetadataGenerator
from asset_processor.models import ProcessedAsset

logger = logging.getLogger(__name__)


class AssetProcessor:
    """Prepare every image before it reaches the renderer.

    Pipeline::

        Raw → Background Removal → RGBA/Normalize → Resize → Validate
            → Metadata → Cache → Processed Asset

    The HF background model is loaded once and reused across images.
    """

    def __init__(self, config: AssetProcessorConfig | None = None) -> None:
        self.config = config or AssetProcessorConfig()
        self.config.ensure_directories()

        self.cache = AssetCache(self.config.cache_directory)
        self.validator = AssetValidator(self.config)
        self.remover = BackgroundRemover(self.config)
        self.normalizer = ImageNormalizer()
        self.resizer = ImageResizer(target_size=self.config.target_size)
        self.metadata = MetadataGenerator()

    def process(self, path: Path | str) -> ProcessedAsset:
        """Process one image; return ``ProcessedAsset`` (uses cache when possible)."""
        started = time.perf_counter()
        source = Path(path)
        if not source.is_file():
            # Allow relative names under raw_directory.
            candidate = self.config.raw_directory / source.name
            if candidate.is_file():
                source = candidate
            else:
                raise ImageLoadError(f"Asset not found: {path}")

        source = source.resolve()
        print("[Asset Processor]", flush=True)
        print("Loading", flush=True)
        logger.info("Processing %s", source)

        self.validator.validate_readable(source)
        digest = self.cache.file_hash(source)

        cached_meta = self.cache.lookup(digest)
        if cached_meta is not None:
            print("Caching", flush=True)
            public_png, public_json = self._public_paths(source)
            cached_image = self.cache.image_path(digest)
            public_png.parent.mkdir(parents=True, exist_ok=True)
            if (
                not public_png.is_file()
                or public_png.resolve() != cached_image.resolve()
            ):
                shutil.copy2(cached_image, public_png)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            meta = cached_meta
            meta.processed_filename = public_png.name
            meta.processed_path = str(public_png)
            meta.cached = True
            meta.processing_time_ms = round(elapsed_ms, 2)
            self.metadata.write(meta, public_json)
            print("Done", flush=True)
            return ProcessedAsset(
                processed_path=public_png,
                metadata=meta,
                processing_time=elapsed_ms / 1000.0,
                cached=True,
            )

        with Image.open(source) as im:
            image = im.copy()

        background_removed = False
        if self.config.remove_background:
            print("Removing Background", flush=True)
            if not self.remover.is_loaded:
                self.remover.load_model()
            image = self.remover.remove_background(image)
            background_removed = True

        print("Normalizing", flush=True)
        image = self.normalizer.normalize(image)

        print("Resizing", flush=True)
        image = self.resizer.resize(image)

        public_png, public_json = self._public_paths(source)
        public_png.parent.mkdir(parents=True, exist_ok=True)
        image.save(public_png, format="PNG")

        print("Validating", flush=True)
        facts = self.validator.validate_processed(public_png)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        print("Generating Metadata", flush=True)
        meta = self.metadata.build(
            original_filename=source.name,
            processed_filename=public_png.name,
            digest=digest,
            width=int(facts["width"]),  # type: ignore[arg-type]
            height=int(facts["height"]),  # type: ignore[arg-type]
            channels=int(facts["channels"]),  # type: ignore[arg-type]
            transparent=bool(facts["transparent"]),
            background_removed=background_removed,
            processing_time_ms=elapsed_ms,
            version=self.config.pipeline_version,
            source_path=str(source),
            processed_path=str(public_png),
            target_size=self.config.target_size,
            cached=False,
        )
        self.metadata.write(meta, public_json)

        print("Caching", flush=True)
        self.cache.store(digest, public_png, meta)

        print("Done", flush=True)
        return ProcessedAsset(
            processed_path=public_png,
            metadata=meta,
            processing_time=elapsed_ms / 1000.0,
            cached=False,
        )

    def process_directory(
        self,
        folder: Path | str | None = None,
        *,
        recursive: bool = False,
    ) -> list[ProcessedAsset]:
        """Process all supported images in a folder."""
        root = Path(folder) if folder is not None else self.config.raw_directory
        if not root.is_dir():
            raise ImageLoadError(f"Directory not found: {root}")

        pattern = "**/*" if recursive else "*"
        paths = sorted(
            p
            for p in root.glob(pattern)
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        results: list[ProcessedAsset] = []
        errors: list[tuple[Path, str]] = []
        for path in paths:
            try:
                results.append(self.process(path))
            except AssetProcessorError as exc:
                logger.error("Failed %s: %s", path, exc)
                errors.append((path, str(exc)))

        if errors and not results:
            raise ImageLoadError(
                f"All {len(errors)} images failed in {root}"
            )
        return results

    def _public_paths(self, source: Path) -> tuple[Path, Path]:
        """``processed_assets/{stem}.png`` and ``processed_assets/{stem}.json``."""
        stem = source.stem
        png = self.config.output_directory / f"{stem}.png"
        js = self.config.output_directory / f"{stem}.json"
        return png, js
