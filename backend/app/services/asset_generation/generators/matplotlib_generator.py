"""Matplotlib generator — educational charts as transparent PNGs."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.asset_generation.generators._drawing import extract_nodes, wrap_label
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


class MatplotlibGenerator(AssetGenerator):
    def generator_type(self) -> GeneratorType:
        return GeneratorType.MATPLOTLIB

    def supports(self, plan: ScenePlan) -> bool:
        return plan.intent.visual_type.value == "chart"

    def estimate_time(self, plan: ScenePlan) -> float:
        return 0.4

    def estimate_memory(self, plan: ScenePlan) -> float:
        return 80.0

    def generate(self, plan: ScenePlan, output_dir: Path) -> GenerationResult:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        started = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        labels = extract_nodes(plan.scene_id, plan.intent.reasoning, plan.intent.matched_keywords, limit=6)
        values = [max(1, (i + 1) * 3) for i in range(len(labels))]
        chart_kind = self._kind(plan)

        fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=100)
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        title = wrap_label(plan.scene_id.replace("-", " ").title(), max_chars=48)

        if chart_kind == "pie":
            ax.pie(values, labels=[wrap_label(l, max_chars=12) for l in labels], autopct="%1.0f%%")
            ax.set_title(title)
        elif chart_kind == "line":
            ax.plot(range(len(values)), values, marker="o", color="#2563eb")
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels([wrap_label(l, max_chars=10) for l in labels], rotation=20)
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
        elif chart_kind == "scatter":
            ax.scatter(range(len(values)), values, s=80, c="#7c3aed")
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels([wrap_label(l, max_chars=10) for l in labels], rotation=20)
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
        elif chart_kind == "hist":
            ax.hist(values * 3, bins=min(8, len(values) + 2), color="#059669", alpha=0.85)
            ax.set_title(title)
        else:
            ax.bar(range(len(values)), values, color="#2563eb")
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels([wrap_label(l, max_chars=10) for l in labels], rotation=20)
            ax.set_title(title)
            ax.grid(True, axis="y", alpha=0.3)

        png_path = output_dir / f"{plan.scene_id}.png"
        fig.savefig(png_path, transparent=True, bbox_inches="tight")
        plt.close(fig)

        elapsed = round(time.perf_counter() - started, 4)
        meta = AssetMetadata(
            scene_id=plan.scene_id,
            generator=GeneratorType.MATPLOTLIB,
            asset_type=AssetType.CHART,
            content_hash="",
            width=960,
            height=540,
            generation_time_sec=elapsed,
            source_visual_type=plan.intent.visual_type.value,
            source_renderer=plan.strategy.primary_renderer.value,
            layers=["foreground", "labels"],
            extra={"chart_kind": chart_kind, "labels": labels, "values": values},
        )
        asset = GeneratedAsset(
            asset_id=str(uuid.uuid4()),
            scene_id=plan.scene_id,
            asset_type=AssetType.CHART,
            format=AssetFormat.PNG,
            path=str(png_path),
            generator=GeneratorType.MATPLOTLIB,
            status=AssetStatus.GENERATED,
            width=960,
            height=540,
            generation_time_sec=elapsed,
            metadata=meta,
        )
        return GenerationResult(
            scene_id=plan.scene_id,
            generator=GeneratorType.MATPLOTLIB,
            status=AssetStatus.GENERATED,
            assets=[asset],
            primary_path=str(png_path),
            generation_time_sec=elapsed,
            detail=f"matplotlib {chart_kind}",
            metadata=meta,
        )

    @staticmethod
    def _kind(plan: ScenePlan) -> str:
        corpus = " ".join(plan.intent.matched_keywords).lower() + " " + plan.intent.reasoning.lower()
        if "pie" in corpus:
            return "pie"
        if "line" in corpus or "growth" in corpus:
            return "line"
        if "scatter" in corpus:
            return "scatter"
        if "hist" in corpus or "distribution" in corpus:
            return "hist"
        return "bar"
