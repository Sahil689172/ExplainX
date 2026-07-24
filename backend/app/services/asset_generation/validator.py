"""Validate generated asset files (SVG / PNG / metadata)."""

from __future__ import annotations

from pathlib import Path

from app.core.errors import ValidationAppError
from app.services.asset_generation.models import AssetFormat, GeneratedAsset, GenerationResult


class AssetValidator:
    """Reject missing, empty, or unreadable generated assets."""

    def __init__(
        self,
        *,
        min_bytes: int = 32,
        min_dimension: int = 8,
        max_dimension: int = 8192,
    ) -> None:
        self.min_bytes = min_bytes
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension

    def validate_result(self, result: GenerationResult) -> GenerationResult:
        if not result.assets:
            raise ValidationAppError(
                "Generation produced no assets.",
                code="ASSET_GENERATION_EMPTY",
                details={"scene_id": result.scene_id, "generator": result.generator.value},
            )
        for asset in result.assets:
            self.validate_asset(asset)
        if result.primary_path and not Path(result.primary_path).is_file():
            raise ValidationAppError(
                "Primary asset path is missing.",
                code="ASSET_PRIMARY_MISSING",
                details={"path": result.primary_path},
            )
        return result

    def validate_asset(self, asset: GeneratedAsset) -> None:
        path = Path(asset.path)
        if not path.is_file():
            raise ValidationAppError(
                f"Asset file missing: {path.name}",
                code="ASSET_FILE_MISSING",
                details={"path": str(path)},
            )
        size = path.stat().st_size
        if size < self.min_bytes:
            raise ValidationAppError(
                f"Asset file empty or too small: {path.name}",
                code="ASSET_FILE_EMPTY",
                details={"path": str(path), "bytes": size},
            )
        if asset.format == AssetFormat.PNG:
            self._validate_png(path)
        elif asset.format == AssetFormat.SVG:
            self._validate_svg(path)
        elif asset.format == AssetFormat.JSON:
            self._validate_json(path)

    def _validate_png(self, path: Path) -> None:
        try:
            from PIL import Image

            with Image.open(path) as img:
                img.load()
                width, height = img.size
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                f"PNG unreadable: {path.name}",
                code="ASSET_PNG_CORRUPT",
                details={"path": str(path), "error": str(exc)},
            ) from exc
        if min(width, height) < self.min_dimension:
            raise ValidationAppError(
                f"PNG too small: {width}x{height}",
                code="ASSET_DIMENSION_INVALID",
                details={"width": width, "height": height},
            )
        if max(width, height) > self.max_dimension:
            raise ValidationAppError(
                f"PNG too large: {width}x{height}",
                code="ASSET_DIMENSION_INVALID",
                details={"width": width, "height": height},
            )

    @staticmethod
    def _validate_svg(path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "<svg" not in text.lower():
            raise ValidationAppError(
                f"SVG missing root element: {path.name}",
                code="ASSET_SVG_INVALID",
                details={"path": str(path)},
            )
        try:
            from lxml import etree
        except ImportError:
            # lxml optional — structural check above is enough.
            return
        try:
            etree.fromstring(text.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                f"SVG XML invalid: {path.name}",
                code="ASSET_SVG_INVALID",
                details={"path": str(path), "error": str(exc)},
            ) from exc

    @staticmethod
    def _validate_json(path: Path) -> None:
        import json

        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                f"JSON metadata invalid: {path.name}",
                code="ASSET_JSON_INVALID",
                details={"path": str(path), "error": str(exc)},
            ) from exc
