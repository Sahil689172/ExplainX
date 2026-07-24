"""SVG generator — educational diagrams via svgwrite."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.asset_generation.generators._drawing import extract_nodes, rasterize_boxes_png, wrap_label
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

_SUPPORTED = frozenset(
    {"diagram", "mathematical", "scientific", "table", "illustration", "text_only", "map", "photo"}
)


class SVGGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.SVG

    def supports(self, plan: ScenePlan) -> bool:
        return plan.intent.visual_type.value in _SUPPORTED

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.12

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 24.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes = extract_nodes(plan.scene_id, plan.intent.reasoning, plan.intent.matched_keywords)
        title = plan.scene_id.replace("-", " ").title()
        kind = self._kind(plan)

        svg_path = output_dir / f"{plan.scene_id}.svg"
        if kind == "cycle":
            self._draw_cycle(svg_path, nodes, title)
        elif kind == "pyramid":
            self._draw_pyramid(svg_path, nodes, title)
        elif kind == "table":
            self._draw_table(svg_path, nodes, title)
        else:
            self._draw_boxes(svg_path, nodes, title)

        png_path = output_dir / f"{plan.scene_id}.png"
        width, height = rasterize_boxes_png(
            png_path, title=title, boxes=nodes, fill=(14, 165, 233, 255)
        )
        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.SVG,
            asset_type=AssetType.DIAGRAM,
            content_hash="",
            width=width,
            height=height,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["diagram", "labels"],
            extra={"svg_kind": kind},
        )
        assets = [
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.DIAGRAM,
                format=AssetFormat.SVG,
                path=str(svg_path),
                generator=GeneratorType.SVG,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.DIAGRAM,
                format=AssetFormat.PNG,
                path=str(png_path),
                generator=GeneratorType.SVG,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
        ]
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.SVG,
            status=AssetStatus.GENERATED,
            assets=assets,
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail=f"svg {kind}",
            metadata=meta,
        )

    @staticmethod
    def _kind(plan: ScenePlan) -> str:
        corpus = " ".join(plan.intent.matched_keywords).lower() + plan.intent.reasoning.lower()
        if plan.intent.visual_type.value == "table" or "table" in corpus:
            return "table"
        if "cycle" in corpus or "stages" in corpus:
            return "cycle"
        if "pyramid" in corpus or "hierarchy" in corpus:
            return "pyramid"
        return "boxes"

    @staticmethod
    def _draw_boxes(path: Path, nodes: list[str], title: str) -> None:
        from app.services.asset_generation.generators._svg import drawing

        w, h = 960, 540
        dwg = drawing(path, width=w, height=h)
        dwg.rect(insert=(0, 0), size=(w, h), fill="#fff7ed")
        dwg.text(wrap_label(title, max_chars=48), insert=(40, 36), fill="#7c2d12", font_size=18)
        y = 80
        for label in nodes:
            dwg.rect(insert=(100, y), size=(w - 200, 50), rx=8, fill="#ea580c")
            dwg.text(wrap_label(label, max_chars=36), insert=(120, y + 32), fill="#fff", font_size=15)
            y += 70
        dwg.save()

    @staticmethod
    def _draw_cycle(path: Path, nodes: list[str], title: str) -> None:
        import math

        from app.services.asset_generation.generators._svg import drawing

        w, h = 960, 540
        dwg = drawing(path, width=w, height=h)
        dwg.rect(insert=(0, 0), size=(w, h), fill="#f0fdf4")
        dwg.text(wrap_label(title, max_chars=48), insert=(40, 36), fill="#14532d", font_size=18)
        cx, cy, r = w / 2, h / 2 + 20, 160
        n = max(1, len(nodes))
        for i, label in enumerate(nodes):
            ang = -math.pi / 2 + (2 * math.pi * i / n)
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
            dwg.circle(center=(x, y), r=42, fill="#16a34a")
            dwg.text(wrap_label(label, max_chars=10), insert=(x - 28, y + 5), fill="#fff", font_size=11)
        dwg.save()

    @staticmethod
    def _draw_pyramid(path: Path, nodes: list[str], title: str) -> None:
        from app.services.asset_generation.generators._svg import drawing

        w, h = 960, 540
        dwg = drawing(path, width=w, height=h)
        dwg.rect(insert=(0, 0), size=(w, h), fill="#eff6ff")
        dwg.text(wrap_label(title, max_chars=48), insert=(40, 36), fill="#1e3a8a", font_size=18)
        n = max(1, len(nodes))
        for i, label in enumerate(nodes):
            frac = (i + 1) / n
            bw = int(200 + 500 * frac)
            x = (w - bw) // 2
            y = 70 + i * 70
            dwg.rect(insert=(x, y), size=(bw, 50), fill="#3b82f6")
            dwg.text(wrap_label(label, max_chars=30), insert=(x + 16, y + 32), fill="#fff", font_size=14)
        dwg.save()

    @staticmethod
    def _draw_table(path: Path, nodes: list[str], title: str) -> None:
        from app.services.asset_generation.generators._svg import drawing

        w, h = 960, 540
        dwg = drawing(path, width=w, height=h)
        dwg.rect(insert=(0, 0), size=(w, h), fill="#fafafa")
        dwg.text(wrap_label(title, max_chars=48), insert=(40, 36), fill="#111", font_size=18)
        row_h = 44
        y = 70
        dwg.rect(insert=(60, y), size=(w - 120, row_h), fill="#e5e7eb")
        dwg.text("Concept", insert=(80, y + 28), fill="#111", font_size=14)
        dwg.text("Role", insert=(480, y + 28), fill="#111", font_size=14)
        y += row_h
        for i, label in enumerate(nodes):
            fill = "#ffffff" if i % 2 == 0 else "#f3f4f6"
            dwg.rect(insert=(60, y), size=(w - 120, row_h), fill=fill, stroke="#d1d5db")
            dwg.text(wrap_label(label, max_chars=28), insert=(80, y + 28), fill="#111", font_size=13)
            dwg.text(f"Item {i + 1}", insert=(480, y + 28), fill="#4b5563", font_size=13)
            y += row_h
        dwg.save()
