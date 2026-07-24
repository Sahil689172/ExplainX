"""Mermaid generator — flowcharts / sequence / state as .mmd + SVG + PNG preview."""

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

_SUPPORTED = frozenset({"flowchart", "diagram", "timeline"})


class MermaidGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.MERMAID

    def supports(self, plan: ScenePlan) -> bool:
        return plan.intent.visual_type.value in _SUPPORTED

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.15

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 32.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes = extract_nodes(
            plan.intent.reasoning[:40],
            "",
            plan.intent.matched_keywords or [plan.scene_id],
        )
        # Prefer layered scene title via strategy scene_id; use keywords.
        title = plan.scene_id.replace("-", " ").title()
        diagram_kind = self._diagram_kind(plan)

        mmd_path = output_dir / f"{plan.scene_id}.mmd"
        mmd_path.write_text(self._mmd_source(diagram_kind, nodes, title), encoding="utf-8")

        svg_path = output_dir / f"{plan.scene_id}.svg"
        self._write_svg(svg_path, nodes, title)

        png_path = output_dir / f"{plan.scene_id}.png"
        width, height = rasterize_boxes_png(png_path, title=title, boxes=nodes)

        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.MERMAID,
            asset_type=AssetType.FLOWCHART,
            content_hash="",
            width=width,
            height=height,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["diagram", "labels"],
            extra={"diagram_kind": diagram_kind, "nodes": nodes},
        )
        assets = [
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.FLOWCHART,
                format=AssetFormat.MMD,
                path=str(mmd_path),
                generator=GeneratorType.MERMAID,
                status=AssetStatus.GENERATED,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.FLOWCHART,
                format=AssetFormat.SVG,
                path=str(svg_path),
                generator=GeneratorType.MERMAID,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
            GeneratedAsset(
                asset_id=str(uuid.uuid4()),
                scene_id=plan.scene_id,
                asset_type=AssetType.FLOWCHART,
                format=AssetFormat.PNG,
                path=str(png_path),
                generator=GeneratorType.MERMAID,
                status=AssetStatus.GENERATED,
                width=width,
                height=height,
                generation_time_sec=elapsed,
                metadata=meta,
            ),
        ]
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.MERMAID,
            status=AssetStatus.GENERATED,
            assets=assets,
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail=f"mermaid {diagram_kind} with {len(nodes)} nodes",
            metadata=meta,
        )

    @staticmethod
    def _diagram_kind(plan: ScenePlan) -> str:
        corpus = " ".join(plan.intent.matched_keywords).lower() + " " + plan.intent.reasoning.lower()
        if "sequence" in corpus or "request" in corpus:
            return "sequence"
        if "state" in corpus:
            return "state"
        if plan.intent.visual_type.value == "timeline":
            return "timeline"
        return "flowchart"

    @staticmethod
    def _mmd_source(kind: str, nodes: list[str], title: str) -> str:
        safe = [n.replace('"', "'") for n in nodes]
        if kind == "sequence":
            lines = ["sequenceDiagram", f"    participant A as {safe[0]}"]
            if len(safe) > 1:
                lines.append(f"    participant B as {safe[1]}")
                lines.append(f"    A->>B: {safe[0]}")
                lines.append(f"    B-->>A: {safe[-1]}")
            return "\n".join(lines) + "\n"
        if kind == "state":
            lines = ["stateDiagram-v2", f"    [*] --> {safe[0]}"]
            for a, b in zip(safe, safe[1:]):
                lines.append(f"    {a} --> {b}")
            lines.append(f"    {safe[-1]} --> [*]")
            return "\n".join(lines) + "\n"
        lines = ["flowchart TD", f"    %% {title}"]
        for i, node in enumerate(safe):
            lines.append(f'    N{i}["{node}"]')
        for i in range(len(safe) - 1):
            lines.append(f"    N{i} --> N{i + 1}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _write_svg(path: Path, nodes: list[str], title: str) -> None:
        from app.services.asset_generation.generators._drawing import wrap_label
        from app.services.asset_generation.generators._svg import drawing

        width, height = 960, 540
        dwg = drawing(path, width=width, height=height)
        dwg.rect(insert=(0, 0), size=(width, height), fill="#f8fafc")
        dwg.text(wrap_label(title, max_chars=50), insert=(40, 36), fill="#0f172a", font_size=18)
        box_h = 56
        y = 70
        for i, label in enumerate(nodes):
            dwg.rect(
                insert=(80, y),
                size=(width - 160, box_h),
                rx=10,
                ry=10,
                fill="#2563eb",
            )
            dwg.text(
                wrap_label(label, max_chars=40),
                insert=(100, y + 34),
                fill="#ffffff",
                font_size=16,
            )
            if i < len(nodes) - 1:
                cx = width // 2
                dwg.line(
                    start=(cx, y + box_h),
                    end=(cx, y + box_h + 20),
                    stroke="#64748b",
                    stroke_width=3,
                )
            y += box_h + 28
        dwg.save()
