"""Render diagnostics artifact (Phase 4.5)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.features.renderer.asset_quality import AssetInfo


class AssetDiagnostic(BaseModel):
    label: str
    role: str
    path: str
    original_size: str
    display_width: int | None = None
    scale: float
    display_size: str
    transparency: bool
    object_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class SceneDiagnostic(BaseModel):
    scene_id: str
    scene_resolution: str
    camera_type: str
    camera_easing: str
    camera_start_scale: float
    camera_end_scale: float
    layered: bool
    object_count: int
    assets: list[AssetDiagnostic] = Field(default_factory=list)


class RenderDiagnostics(BaseModel):
    """Persisted quality / normalization summary for one render run."""

    output_resolution: str
    scene_resolution: str | None = None
    camera_smoothing: str = "ease_in_out"
    viewport_precision: str = "float_until_crop"
    crop_source: str = "original_composed_scene"
    scenes: list[SceneDiagnostic] = Field(default_factory=list)
    assets: list[AssetDiagnostic] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @staticmethod
    def from_asset(info: AssetInfo) -> AssetDiagnostic:
        dw, dh = info.display_size
        return AssetDiagnostic(
            label=info.label,
            role=info.role,
            path=str(info.path),
            original_size=f"{info.width}x{info.height}",
            display_width=info.display_width,
            scale=round(info.scale, 6),
            display_size=f"{dw}x{dh}",
            transparency=info.has_alpha,
            object_id=info.object_id,
            warnings=list(info.warnings),
        )
