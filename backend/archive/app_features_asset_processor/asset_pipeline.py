"""Asset processing pipeline — prepare images before the renderer."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.features.asset_processor.asset_cache import AssetCache
from app.features.asset_processor.asset_validator import AssetValidator
from app.features.asset_processor.background_remover import BackgroundRemover
from app.features.asset_processor.image_normalizer import ImageNormalizer
from app.features.asset_processor.image_resizer import ImageResizer
from app.features.asset_processor.metadata_generator import MetadataGenerator
from app.features.asset_processor.models import ProcessResult


class AssetProcessor:
    """Public API: ``process(image_path) -> ProcessResult``.

    Pipeline: load → background removal → resize → normalize → validate →
    metadata → cache → processed asset.
    """

    def __init__(
        self,
        *,
        raw_dir: Path,
        processed_dir: Path,
        cache_dir: Path,
        model_dir: Path,
        target_size: int = 512,
        stub_background_removal: bool = False,
        remove_background: bool = True,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.cache_dir = Path(cache_dir)
        self.model_dir = Path(model_dir)
        self.target_size = int(target_size)
        self.remove_background = remove_background

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.cache = AssetCache(self.cache_dir)
        self.remover = BackgroundRemover(
            self.model_dir,
            stub=stub_background_removal,
        )
        self.resizer = ImageResizer(target_size=self.target_size)
        self.normalizer = ImageNormalizer()
        self.validator = AssetValidator()
        self.metadata = MetadataGenerator()

    @classmethod
    def from_data_root(
        cls,
        data_root: Path,
        *,
        target_size: int = 512,
        stub_background_removal: bool = False,
    ) -> AssetProcessor:
        root = Path(data_root)
        return cls(
            raw_dir=root / "raw_assets",
            processed_dir=root / "processed_assets",
            cache_dir=root / "cache" / "assets",
            model_dir=root / "models" / "background_removal",
            target_size=target_size,
            stub_background_removal=stub_background_removal,
        )

    def process(self, image_path: Path | str) -> ProcessResult:
        """Process one image; return processed path + metadata (uses cache)."""
        source = Path(image_path)
        print("[Asset Processor]", flush=True)
        print("Loading", flush=True)

        self.validator.validate_readable(source)
        digest = self.cache.file_hash(source)

        cached_meta = self.cache.lookup(digest)
        if cached_meta is not None:
            cached_image = self.cache.processed_image_path(digest)
            # Mirror into processed_assets for a stable public path.
            public_path = self._public_path(source, digest)
            if not public_path.is_file():
                public_path.parent.mkdir(parents=True, exist_ok=True)
                public_path.write_bytes(cached_image.read_bytes())
                self.metadata.write(
                    cached_meta.model_copy(
                        update={
                            "processed_filename": public_path.name,
                            "processed_path": str(public_path),
                        }
                    ),
                    public_path.with_name(public_path.stem + ".asset.json"),
                )
            print("Cached", flush=True)
            print("Done", flush=True)
            return ProcessResult(
                processed_path=public_path,
                metadata=cached_meta.model_copy(
                    update={
                        "processed_filename": public_path.name,
                        "processed_path": str(public_path),
                    }
                ),
                cached=True,
            )

        with Image.open(source) as im:
            # Fix EXIF orientation before the documented pipeline stages.
            from PIL import ImageOps

            image = ImageOps.exif_transpose(im).copy()

        if self.remove_background:
            print("Removing Background", flush=True)
            image = self.remover.remove(image)
            background_removed = True
        else:
            image = image.convert("RGBA")
            background_removed = False

        print("Resizing", flush=True)
        image = self.resizer.resize(image)

        print("Normalizing", flush=True)
        image = self.normalizer.normalize(image)

        public_path = self._public_path(source, digest)
        public_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(public_path, format="PNG")

        facts = self.validator.validate_processed(public_path)

        print("Generating Metadata", flush=True)
        meta = self.metadata.build(
            original_filename=source.name,
            processed_filename=public_path.name,
            width=int(facts["width"]),  # type: ignore[arg-type]
            height=int(facts["height"]),  # type: ignore[arg-type]
            digest=digest,
            transparent=bool(facts["transparent"]),
            background_removed=background_removed,
            target_size=self.target_size,
            source_path=str(source.resolve()),
            processed_path=str(public_path.resolve()),
        )
        meta_path = public_path.with_name(public_path.stem + ".asset.json")
        self.metadata.write(meta, meta_path)
        self.cache.store(digest, public_path, meta)

        print("Done", flush=True)
        return ProcessResult(processed_path=public_path, metadata=meta, cached=False)

    def _public_path(self, source: Path, digest: str) -> Path:
        stem = source.stem
        return self.processed_dir / f"{stem}_{digest[:12]}.png"
