"""Background generator — educational SVG/PNG backgrounds."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.asset_generation.generators._drawing import save_rgba_png
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


class BackgroundGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.BACKGROUND

    def supports(self, plan: ScenePlan) -> bool:
        return plan.intent.visual_type.value == "background"

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.1

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 20.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        style = self._style(plan)
        width, height = 1280, 720

        svg_path = output_dir / f"{plan.scene_id}_bg.svg"
        self._write_svg(svg_path, style, width, height)

        png_path = output_dir / f"{plan.scene_id}_bg.png"

        def _draw(draw, w: int, h: int) -> None:
            if style == "chalkboard":
                draw.rectangle([0, 0, w, h], fill=(22, 101, 52, 255))
                for x in range(0, w, 40):
                    draw.line([(x, 0), (x, h)], fill=(34, 120, 70, 40), width=1)
            elif style == "grid":
                draw.rectangle([0, 0, w, h], fill=(248, 250, 252, 255))
                for x in range(0, w, 32):
                    draw.line([(x, 0), (x, h)], fill=(203, 213, 225, 255), width=1)
                for y in range(0, h, 32):
                    draw.line([(0, y), (w, y)], fill=(203, 213, 225, 255), width=1)
            elif style == "dots":
                draw.rectangle([0, 0, w, h], fill=(255, 255, 255, 255))
                for x in range(16, w, 24):
                    for y in range(16, h, 24):
                        draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(148, 163, 184, 255))
            elif style == "notebook":
                draw.rectangle([0, 0, w, h], fill=(255, 252, 232, 255))
                for y in range(48, h, 28):
                    draw.line([(40, y), (w - 20, y)], fill=(186, 230, 253, 255), width=2)
                draw.line([(70, 0), (70, h)], fill=(252, 165, 165, 255), width=2)
            else:  # gradient-like bands
                bands = 12
                for i in range(bands):
                    y0 = int(h * i / bands)
                    y1 = int(h * (i + 1) / bands)
                    c = 180 + int(50 * i / bands)
                    draw.rectangle([0, y0, w, y1], fill=(c, 210, 255, 255))

        save_rgba_png(png_path, (width, height), _draw)
        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.BACKGROUND,
            asset_type=AssetType.BACKGROUND,
            content_hash="",
            width=width,
            height=height,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["background"],
            extra={"style": style},
            theme=style,
        )
        assets = [
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.BACKGROUND,
                format=AssetFormat.SVG,
                path=str(svg_path),
                generator=GeneratorType.BACKGROUND,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.BACKGROUND,
                format=AssetFormat.PNG,
                path=str(png_path),
                generator=GeneratorType.BACKGROUND,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
        ]
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.BACKGROUND,
            status=AssetStatus.GENERATED,
            assets=assets,
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail=f"background {style}",
            metadata=meta,
        )

    @staticmethod
    def _style(plan: ScenePlan) -> str:
        corpus = " ".join(plan.intent.matched_keywords).lower() + " " + plan.intent.reasoning.lower()
        for key in ("chalkboard", "grid", "dots", "notebook", "blueprint"):
            if key in corpus:
                return "grid" if key == "blueprint" else key
        return "gradient"

    @staticmethod
    def _write_svg(path: Path, style: str, width: int, height: int) -> None:
        from app.services.asset_generation.generators._svg import drawing

        dwg = drawing(path, width=width, height=height)
        if style == "chalkboard":
            dwg.rect(insert=(0, 0), size=(width, height), fill="#166534")
        elif style == "grid":
            dwg.rect(insert=(0, 0), size=(width, height), fill="#f8fafc")
            for x in range(0, width, 32):
                dwg.line(start=(x, 0), end=(x, height), stroke="#cbd5e1", stroke_width=1)
            for y in range(0, height, 32):
                dwg.line(start=(0, y), end=(width, y), stroke="#cbd5e1", stroke_width=1)
        elif style == "dots":
            dwg.rect(insert=(0, 0), size=(width, height), fill="#ffffff")
            for x in range(16, width, 24):
                for y in range(16, height, 24):
                    dwg.circle(center=(x, y), r=2, fill="#94a3b8")
        elif style == "notebook":
            dwg.rect(insert=(0, 0), size=(width, height), fill="#fffceb")
            for y in range(48, height, 28):
                dwg.line(start=(40, y), end=(width - 20, y), stroke="#bae6fd", stroke_width=2)
            dwg.line(start=(70, 0), end=(70, height), stroke="#fca5a5", stroke_width=2)
        else:
            dwg.rect(insert=(0, 0), size=(width, height), fill="#bfdbfe")
        dwg.save()
