"""Validate raw and processed image assets."""

from __future__ import annotations

from pathlib import Path

from asset_processor.config import SUPPORTED_EXTENSIONS, AssetProcessorConfig
from asset_processor.exceptions import ImageLoadError, UnsupportedFormatError, ValidationError


class AssetValidator:
    """Hard validation gate for pipeline inputs and outputs."""

    def __init__(self, config: AssetProcessorConfig) -> None:
        self.config = config

    def validate_extension(self, path: Path) -> None:
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported extension {suffix!r}. "
                f"Allowed: {sorted(SUPPORTED_EXTENSIONS)}"
            )

    def validate_readable(self, path: Path) -> None:
        if not path.is_file():
            raise ImageLoadError(f"Asset not found: {path}")
        self.validate_extension(path)
        try:
            from PIL import Image

            with Image.open(path) as im:
                im.verify()
            # verify() invalidates the handle; reopen to fully load.
            with Image.open(path) as im:
                im.load()
        except ValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ImageLoadError(f"Corrupted or unreadable image: {path.name}") from exc

    def validate_processed(self, path: Path) -> dict[str, object]:
        """Validate a processed RGBA PNG. Returns facts for metadata."""
        self.validate_readable(path)
        from PIL import Image

        with Image.open(path) as im:
            mode = im.mode
            width, height = im.size

            if mode not in {"RGBA", "LA", "RGBa"}:
                raise ValidationError(
                    f"Processed asset must be RGBA: {path.name} (mode={mode})"
                )

            if min(width, height) < self.config.min_dimension:
                raise ValidationError(
                    f"Asset too small: {width}x{height} "
                    f"(min={self.config.min_dimension})"
                )
            if max(width, height) > self.config.max_dimension:
                raise ValidationError(
                    f"Asset too large: {width}x{height} "
                    f"(max={self.config.max_dimension})"
                )

            rgba = im.convert("RGBA")
            alpha_ext = rgba.getextrema()[-1]
            transparent = bool(alpha_ext[0] < 255)

            if self.config.require_transparency and not transparent:
                raise ValidationError(f"Asset has no transparency: {path.name}")

            channels = len(rgba.getbands())

        return {
            "width": width,
            "height": height,
            "channels": channels,
            "transparent": transparent,
            "mode": "RGBA",
        }
