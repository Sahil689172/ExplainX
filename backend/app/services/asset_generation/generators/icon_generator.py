"""Icon generator — compose simple local SVG/PNG educational icons."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.asset_generation.generators._drawing import save_rgba_png, wrap_label
from app.services.asset_generation.interfaces import AssetGenerator
from app.services.asset_generation.models import (
    AssetFormat,
    AssetMetadata,
    AssetStatus,
    AssetType,
    GeneratedAsset,
    GenerationResult,
    GeneratorType,
)

if TYPE_CHECKING:
    from app.services.visual_intelligence.service import ScenePlan


class IconGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.ICON

    def supports(self, plan: ScenePlan) -> bool:
        return plan.intent.visual_type.value == "icon"

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.08

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 16.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        labels = plan.intent.matched_keywords[:4] or ["concept", "idea"]
        color = (79, 70, 229, 255)

        svg_path = output_dir / f"{plan.scene_id}_icons.svg"
        self._write_svg_strip(svg_path, labels, color)

        png_path = output_dir / f"{plan.scene_id}_icons.png"

        def _draw(draw, width: int, height: int) -> None:
            from PIL import ImageFont

            font = ImageFont.load_default()
            draw.rectangle([0, 0, width, height], fill=(255, 255, 255, 0))
            slot = width // max(1, len(labels))
            for i, label in enumerate(labels):
                cx = slot * i + slot // 2
                cy = height // 2
                r = min(40, slot // 3)
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
                draw.text((cx - 20, cy + r + 8), wrap_label(label, max_chars=10), fill=(30, 30, 30, 255), font=font)

        width, height = save_rgba_png(png_path, (640, 240), _draw)
        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.ICON,
            asset_type=AssetType.ICON,
            content_hash="",
            width=width,
            height=height,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["icons"],
            extra={"icons": labels},
        )
        assets = [
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.ICON,
                format=AssetFormat.SVG,
                path=str(svg_path),
                generator=GeneratorType.ICON,
                status=AssetStatus.GENERATED,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.ICON,
                format=AssetFormat.PNG,
                path=str(png_path),
                generator=GeneratorType.ICON,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
        ]
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.ICON,
            status=AssetStatus.GENERATED,
            assets=assets,
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail=f"{len(labels)} icons",
            metadata=meta,
        )

    @staticmethod
    def _write_svg_strip(path: Path, labels: list[str], color: tuple[int, int, int, int]) -> None:
        from app.services.asset_generation.generators._svg import drawing

        w, h = 640, 240
        dwg = drawing(path, width=w, height=h)
        fill = f"rgb({color[0]},{color[1]},{color[2]})"
        slot = w // max(1, len(labels))
        for i, label in enumerate(labels):
            cx = slot * i + slot // 2
            cy = h // 2 - 10
            dwg.circle(center=(cx, cy), r=36, fill=fill)
            dwg.text(wrap_label(label, max_chars=10), insert=(cx - 24, cy + 55), fill="#111", font_size=12)
        dwg.save()
