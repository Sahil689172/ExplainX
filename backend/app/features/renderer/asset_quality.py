"""Asset quality helpers — transparency, sizing, validation (Phase 4.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.features.renderer.frame_renderer import read_image_resolution

# Soft-warning thresholds (do not fail the render).
_MIN_RECOMMENDED_PX = 32
_MAX_RECOMMENDED_PX = 4096


@dataclass(slots=True)
class AssetInfo:
    """Normalized facts about one background or object image."""

    path: Path
    label: str
    width: int
    height: int
    has_alpha: bool
    scale: float = 1.0
    display_width: int | None = None
    object_id: str | None = None
    role: str = "object"  # object | background
    warnings: list[str] = field(default_factory=list)

    @property
    def display_size(self) -> tuple[int, int]:
        """Pixel size after logical scale (aspect preserved)."""
        w = max(1, int(round(self.width * self.scale)))
        h = max(1, int(round(self.height * self.scale)))
        return w, h


def detect_transparency(path: Path) -> bool:
    """Return True when the image has usable alpha / palette transparency."""
    try:
        from PIL import Image
    except ImportError:
        return path.suffix.lower() == ".png"

    with Image.open(path) as im:
        if im.mode in {"RGBA", "LA", "RGBa"}:
            extrema = im.getextrema()
            # Alpha channel extrema is last tuple for RGBA/LA.
            alpha_ext = extrema[-1] if isinstance(extrema[-1], tuple) else (0, 255)
            return alpha_ext[0] < 255
        if im.mode == "P":
            if "transparency" in im.info:
                return True
            # Convert palette images that may carry transparency.
            rgba = im.convert("RGBA")
            alpha_ext = rgba.getextrema()[-1]
            return alpha_ext[0] < 255
        return False


def resolve_display_scale(
    *,
    image_width: int,
    scale: float = 1.0,
    display_width: int | None = None,
) -> float:
    """Compute uniform scale from ``display_width`` (preferred) or legacy ``scale``."""
    if display_width is not None:
        if display_width <= 0:
            raise ValueError("display_width must be > 0")
        if image_width <= 0:
            raise ValueError("image_width must be > 0")
        return float(display_width) / float(image_width)
    return float(scale)


def inspect_asset(
    path: Path,
    *,
    label: str | None = None,
    role: str = "object",
    object_id: str | None = None,
    scale: float = 1.0,
    display_width: int | None = None,
) -> AssetInfo:
    """Load dimensions / transparency and collect soft warnings."""
    name = label or path.name
    width, height = read_image_resolution(path)
    has_alpha = detect_transparency(path)
    resolved_scale = resolve_display_scale(
        image_width=width,
        scale=scale,
        display_width=display_width,
    )
    info = AssetInfo(
        path=path,
        label=name,
        width=width,
        height=height,
        has_alpha=has_alpha,
        scale=resolved_scale,
        display_width=display_width,
        object_id=object_id,
        role=role,
    )

    if role == "object" and not has_alpha:
        msg = f"{name} has no transparency."
        info.warnings.append(msg)
        print("[Asset Warning]", flush=True)
        print(msg, flush=True)
        print("Future recommendation:", flush=True)
        print("Convert asset to transparent PNG.", flush=True)

    if min(width, height) < _MIN_RECOMMENDED_PX:
        info.warnings.append(
            f"{name} is very small ({width}x{height})."
        )
        print("[Asset Warning]", flush=True)
        print(f"{name} is very small ({width}x{height}).", flush=True)

    if max(width, height) > _MAX_RECOMMENDED_PX:
        info.warnings.append(
            f"{name} is very large ({width}x{height})."
        )
        print("[Asset Warning]", flush=True)
        print(f"{name} is very large ({width}x{height}).", flush=True)

    return info


def log_asset(info: AssetInfo) -> None:
    """Print Phase 4.5 asset diagnostics."""
    dw, dh = info.display_size
    print("[Asset]", flush=True)
    print(info.label, flush=True)
    print("Original", flush=True)
    print(f"{info.width} x {info.height}", flush=True)
    if info.display_width is not None:
        print("Display Width", flush=True)
        print(str(info.display_width), flush=True)
    print("Scale", flush=True)
    print(f"{info.scale:.4g}", flush=True)
    print("Display Size", flush=True)
    print(f"{dw} x {dh}", flush=True)
    print("Transparency", flush=True)
    print("YES" if info.has_alpha else "NO", flush=True)


def log_renderer_output(width: int, height: int) -> None:
    print("[Renderer]", flush=True)
    print("Output", flush=True)
    print(f"{width} x {height}", flush=True)
