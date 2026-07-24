"""Timeline generator — horizontal / vertical educational timelines."""

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


class TimelineGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.TIMELINE

    def supports(self, plan: ScenePlan) -> bool:
        # Prefer mermaid for timeline when both support; registry priority handles that.
        # Still support so fallback / explicit selection works.
        return plan.intent.visual_type.value == "timeline"

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.14

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 28.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes = extract_nodes(plan.scene_id, plan.intent.reasoning, plan.intent.matched_keywords)
        vertical = "vertical" in " ".join(plan.intent.matched_keywords).lower()
        title = plan.scene_id.replace("-", " ").title()

        svg_path = output_dir / f"{plan.scene_id}_timeline.svg"
        self._write_svg(svg_path, nodes, title, vertical=vertical)

        png_path = output_dir / f"{plan.scene_id}_timeline.png"

        def _draw(draw, w: int, h: int) -> None:
            from PIL import ImageFont

            font = ImageFont.load_default()
            draw.rectangle([0, 0, w, h], fill=(255, 255, 255, 255))
            draw.text((30, 20), wrap_label(title, max_chars=40), fill=(15, 23, 42, 255), font=font)
            if vertical:
                x = w // 2
                draw.line([(x, 60), (x, h - 40)], fill=(59, 130, 246, 255), width=4)
                step = (h - 120) // max(1, len(nodes) - 1) if len(nodes) > 1 else 0
                for i, label in enumerate(nodes):
                    y = 60 + i * step
                    draw.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(37, 99, 235, 255))
                    draw.text((x + 20, y - 6), wrap_label(label, max_chars=28), fill=(30, 41, 59, 255), font=font)
            else:
                y = h // 2
                draw.line([(40, y), (w - 40, y)], fill=(59, 130, 246, 255), width=4)
                step = (w - 120) // max(1, len(nodes) - 1) if len(nodes) > 1 else 0
                for i, label in enumerate(nodes):
                    x = 60 + i * step
                    draw.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(37, 99, 235, 255))
                    draw.text((x - 30, y + 18), wrap_label(label, max_chars=14), fill=(30, 41, 59, 255), font=font)

        width, height = save_rgba_png(png_path, (960, 540), _draw)
        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.TIMELINE,
            asset_type=AssetType.TIMELINE,
            content_hash="",
            width=width,
            height=height,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["diagram", "labels"],
            extra={"orientation": "vertical" if vertical else "horizontal", "nodes": nodes},
        )
        assets = [
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.TIMELINE,
                format=AssetFormat.SVG,
                path=str(svg_path),
                generator=GeneratorType.TIMELINE,
                status=AssetStatus.GENERATED,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.TIMELINE,
                format=AssetFormat.PNG,
                path=str(png_path),
                generator=GeneratorType.TIMELINE,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
        ]
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.TIMELINE,
            status=AssetStatus.GENERATED,
            assets=assets,
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail="timeline " + ("vertical" if vertical else "horizontal"),
            metadata=meta,
        )

    @staticmethod
    def _write_svg(path: Path, nodes: list[str], title: str, *, vertical: bool) -> None:
        from app.services.asset_generation.generators._svg import drawing

        w, h = 960, 540
        dwg = drawing(path, width=w, height=h)
        dwg.rect(insert=(0, 0), size=(w, h), fill="#ffffff")
        dwg.text(wrap_label(title, max_chars=40), insert=(30, 36), fill="#0f172a", font_size=18)
        if vertical:
            x = w // 2
            dwg.line(start=(x, 60), end=(x, h - 40), stroke="#3b82f6", stroke_width=4)
            step = (h - 120) // max(1, len(nodes) - 1) if len(nodes) > 1 else 0
            for i, label in enumerate(nodes):
                y = 60 + i * step
                dwg.circle(center=(x, y), r=10, fill="#2563eb")
                dwg.text(wrap_label(label, max_chars=28), insert=(x + 20, y + 5), fill="#1e293b", font_size=13)
        else:
            y = h // 2
            dwg.line(start=(40, y), end=(w - 40, y), stroke="#3b82f6", stroke_width=4)
            step = (w - 120) // max(1, len(nodes) - 1) if len(nodes) > 1 else 0
            for i, label in enumerate(nodes):
                x = 60 + i * step
                dwg.circle(center=(x, y), r=10, fill="#2563eb")
                dwg.text(wrap_label(label, max_chars=14), insert=(x - 30, y + 30), fill="#1e293b", font_size=12)
        dwg.save()
