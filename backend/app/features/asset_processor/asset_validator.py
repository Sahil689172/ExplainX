"""Validate processed (and raw) image assets."""

from __future__ import annotations

from pathlib import Path

from app.core.errors import ValidationAppError

_MIN_SIZE = 8
_MAX_SIZE = 8192


class AssetValidator:
    """Soft/hard checks for asset pipeline outputs."""

    def __init__(
        self,
        *,
        min_size: int = _MIN_SIZE,
        max_size: int = _MAX_SIZE,
        require_transparency: bool = False,
    ) -> None:
        self.min_size = min_size
        self.max_size = max_size
        self.require_transparency = require_transparency

    def validate_readable(self, path: Path) -> None:
        if not path.is_file():
            raise ValidationAppError(
                f"Asset not found: {path}",
                code="ASSET_NOT_FOUND",
                details={"path": str(path)},
            )
        try:
            from PIL import Image

            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
        except Exception as exc:  # noqa: BLE001 — surface as validation error
            raise ValidationAppError(
                f"Asset is not a readable image: {path.name}",
                code="ASSET_CORRUPTED",
                details={"path": str(path), "error": str(exc)},
            ) from exc

    def validate_processed(self, path: Path) -> dict[str, object]:
        """Validate a processed RGBA asset. Returns facts used by metadata."""
        self.validate_readable(path)
        from PIL import Image

        with Image.open(path) as im:
            mode = im.mode
            width, height = im.size
            has_alpha = mode in {"RGBA", "LA", "RGBa"} or (
                mode == "P" and "transparency" in im.info
            )
            if mode not in {"RGBA", "LA", "RGBa"}:
                # Allow palette with transparency only if convertible.
                if mode == "P" and "transparency" in im.info:
                    has_alpha = True
                else:
                    raise ValidationAppError(
                        f"Processed asset must be RGBA: {path.name} (mode={mode})",
                        code="ASSET_NOT_RGBA",
                        details={"path": str(path), "mode": mode},
                    )

            if min(width, height) < self.min_size:
                raise ValidationAppError(
                    f"Asset too small: {width}x{height}",
                    code="ASSET_TOO_SMALL",
                    details={"width": width, "height": height},
                )
            if max(width, height) > self.max_size:
                raise ValidationAppError(
                    f"Asset too large: {width}x{height}",
                    code="ASSET_TOO_LARGE",
                    details={"width": width, "height": height},
                )

            transparent = False
            if has_alpha:
                rgba = im.convert("RGBA")
                alpha_ext = rgba.getextrema()[-1]
                transparent = alpha_ext[0] < 255

            if self.require_transparency and not transparent:
                raise ValidationAppError(
                    f"Asset has no transparency: {path.name}",
                    code="ASSET_NO_TRANSPARENCY",
                    details={"path": str(path)},
                )

        return {
            "width": width,
            "height": height,
            "transparent": transparent,
            "mode": "RGBA",
        }
