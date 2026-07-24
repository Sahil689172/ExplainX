"""Compose layered educational assets into a single ScenePackage (no video render)."""

from __future__ import annotations

from pathlib import Path

from app.services.asset_generation.models import (
    AssetBundle,
    AssetFormat,
    AssetType,
    ScenePackage,
)


class SceneComposer:
    """Merge background / diagram / icons / labels into one PNG package.

    Does **not** touch the Timeline Engine or Rendering Engine — only produces a
    composited still image for preview / downstream hand-off.
    """

    def compose(self, bundle: AssetBundle, *, canvas: tuple[int, int] = (1280, 720)) -> ScenePackage:
        from PIL import Image

        scene_id = bundle.scene_id
        export_dir = Path(bundle.export_dir or ".")
        export_dir.mkdir(parents=True, exist_ok=True)

        pngs = [
            a for a in bundle.result.assets if a.format == AssetFormat.PNG and Path(a.path).is_file()
        ]
        background = next((a for a in pngs if a.asset_type == AssetType.BACKGROUND), None)
        diagram = next(
            (
                a
                for a in pngs
                if a.asset_type
                in {
                    AssetType.FLOWCHART,
                    AssetType.DIAGRAM,
                    AssetType.TIMELINE,
                    AssetType.CHART,
                    AssetType.INFOGRAPHIC,
                    AssetType.COMPOSITE,
                }
            ),
            pngs[0] if pngs else None,
        )
        icons = [a for a in pngs if a.asset_type == AssetType.ICON]

        width, height = canvas
        canvas_img = Image.new("RGBA", (width, height), (255, 255, 255, 255))

        if background is not None:
            with Image.open(background.path) as bg:
                canvas_img.alpha_composite(bg.convert("RGBA").resize((width, height)))

        if diagram is not None:
            with Image.open(diagram.path) as fg:
                layer = fg.convert("RGBA")
                # Contain-fit into canvas with margins.
                layer.thumbnail((width - 80, height - 80))
                x = (width - layer.width) // 2
                y = (height - layer.height) // 2
                canvas_img.alpha_composite(layer, dest=(x, y))

        for i, icon in enumerate(icons[:4]):
            with Image.open(icon.path) as ic:
                stamp = ic.convert("RGBA")
                stamp.thumbnail((160, 160))
                canvas_img.alpha_composite(stamp, dest=(40 + i * 180, height - 180))

        composed_path = export_dir / f"{scene_id}_composed.png"
        canvas_img.save(composed_path, format="PNG")

        return ScenePackage(
            scene_id=scene_id,
            background_path=background.path if background else None,
            foreground_path=diagram.path if diagram else None,
            diagram_path=diagram.path if diagram else None,
            chart_path=next((a.path for a in pngs if a.asset_type == AssetType.CHART), None),
            icon_paths=[a.path for a in icons],
            composed_path=str(composed_path),
            metadata={
                "generator": bundle.result.generator.value,
                "cache_hit": bundle.result.cache_hit,
                "content_hash": bundle.result.content_hash,
            },
        )
