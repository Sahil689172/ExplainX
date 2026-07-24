"""Infographic generator — compose SVG boxes + icons + labels."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.asset_generation.generators._drawing import extract_nodes, save_rgba_png, wrap_label
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


class InfographicGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.INFOGRAPHIC

    def supports(self, plan: ScenePlan) -> bool:
        return plan.intent.visual_type.value in {"mixed", "illustration"}

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.25

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 48.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes = extract_nodes(plan.scene_id, plan.intent.reasoning, plan.intent.matched_keywords, limit=4)
        title = plan.scene_id.replace("-", " ").title()

        svg_path = output_dir / f"{plan.scene_id}_infographic.svg"
        self._write_svg(svg_path, nodes, title)

        png_path = output_dir / f"{plan.scene_id}_infographic.png"

        def _draw(draw, w: int, h: int) -> None:
            from PIL import ImageFont

            font = ImageFont.load_default()
            draw.rectangle([0, 0, w, h], fill=(255, 251, 235, 255))
            draw.rectangle([0, 0, w, 64], fill=(245, 158, 11, 255))
            draw.text((24, 22), wrap_label(title, max_chars=42), fill=(255, 255, 255, 255), font=font)
            cols = min(4, max(1, len(nodes)))
            slot = (w - 60) // cols
            for i, label in enumerate(nodes):
                x = 30 + i * slot
                y = 110
                draw.rounded_rectangle([x, y, x + slot - 20, y + 160], radius=16, fill=(254, 243, 199, 255))
                cx, cy = x + (slot - 20) // 2, y + 50
                draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(217, 119, 6, 255))
                draw.text((x + 12, y + 100), wrap_label(label, max_chars=16), fill=(120, 53, 15, 255), font=font)

        width, height = save_rgba_png(png_path, (960, 540), _draw)
        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.INFOGRAPHIC,
            asset_type=AssetType.INFOGRAPHIC,
            content_hash="",
            width=width,
            height=height,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["background", "icons", "labels"],
            extra={"panels": nodes},
        )
        assets = [
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.INFOGRAPHIC,
                format=AssetFormat.SVG,
                path=str(svg_path),
                generator=GeneratorType.INFOGRAPHIC,
                status=AssetStatus.GENERATED,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.INFOGRAPHIC,
                format=AssetFormat.PNG,
                path=str(png_path),
                generator=GeneratorType.INFOGRAPHIC,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
        ]
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.INFOGRAPHIC,
            status=AssetStatus.GENERATED,
            assets=assets,
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail=f"infographic {len(nodes)} panels",
            metadata=meta,
        )

    @staticmethod
    def _write_svg(path: Path, nodes: list[str], title: str) -> None:
        from app.services.asset_generation.generators._svg import drawing

        w, h = 960, 540
        dwg = drawing(path, width=w, height=h)
        dwg.rect(insert=(0, 0), size=(w, h), fill="#fffbeb")
        dwg.rect(insert=(0, 0), size=(w, 64), fill="#f59e0b")
        dwg.text(wrap_label(title, max_chars=42), insert=(24, 40), fill="#fff", font_size=18)
        cols = min(4, max(1, len(nodes)))
        slot = (w - 60) // cols
        for i, label in enumerate(nodes):
            x = 30 + i * slot
            y = 110
            dwg.rect(insert=(x, y), size=(slot - 20, 160), rx=16, fill="#fef3c7")
            cx, cy = x + (slot - 20) / 2, y + 50
            dwg.circle(center=(cx, cy), r=28, fill="#d97706")
            dwg.text(wrap_label(label, max_chars=16), insert=(x + 12, y + 120), fill="#78350f", font_size=12)
        dwg.save()
