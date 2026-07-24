#!/usr/bin/env python
"""Demo: Visual Intelligence ScenePlans → Asset Generation → ScenePackage.

Usage::

    cd backend
    python demo_asset_generation.py

Outputs land in ``demo_output/asset_generation/``.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.asset_generation import AssetGenerationService
from app.services.visual_intelligence import VisualIntelligenceService
from app.services.visual_intelligence.layers import LayeredScene, VisualLayer
from app.services.visual_intelligence.schemas import (
    Complexity,
    LayerType,
    RendererType,
    RenderingStrategy,
    VisualIntent,
    VisualType,
)
from app.services.visual_intelligence.service import ScenePlan

OUT = ROOT / "demo_output" / "asset_generation"


def _manual_plan(
    scene_id: str,
    visual_type: VisualType,
    renderer: RendererType,
    keywords: list[str],
) -> ScenePlan:
    intent = VisualIntent(
        scene_id=scene_id,
        visual_type=visual_type,
        confidence=0.9,
        reasoning=f"Demo {visual_type.value}",
        suggested_renderer=renderer,
        estimated_duration=6.0,
        complexity=Complexity.SIMPLE,
        matched_keywords=keywords,
    )
    strategy = RenderingStrategy(
        scene_id=scene_id,
        visual_type=visual_type,
        primary_renderer=renderer,
        layers=[LayerType.BACKGROUND, LayerType.DIAGRAM],
    )
    layered = LayeredScene(
        scene_id=scene_id,
        duration_sec=6.0,
        layers=[
            VisualLayer(layer_type=LayerType.BACKGROUND, z_index=0),
            VisualLayer(layer_type=LayerType.DIAGRAM, z_index=20, renderer=renderer),
        ],
    )
    return ScenePlan(scene_id=scene_id, intent=intent, strategy=strategy, layered_scene=layered)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cache_dir = OUT / "cache"
    service = AssetGenerationService.with_cache(cache_dir)

    plans = [
        _manual_plan(
            "demo-flowchart",
            VisualType.FLOWCHART,
            RendererType.MERMAID,
            ["request", "process", "response", "sequence"],
        ),
        _manual_plan(
            "demo-svg",
            VisualType.DIAGRAM,
            RendererType.SVG,
            ["cycle", "stages", "diagram"],
        ),
        _manual_plan(
            "demo-chart",
            VisualType.CHART,
            RendererType.MATPLOTLIB,
            ["chart", "growth", "line", "data"],
        ),
        _manual_plan(
            "demo-timeline",
            VisualType.TIMELINE,
            RendererType.SVG,
            ["era", "event", "milestone"],
        ),
        _manual_plan(
            "demo-infographic",
            VisualType.MIXED,
            RendererType.SVG,
            ["idea", "fact", "tip", "summary"],
        ),
    ]

    # Also plan from a mini EducationalScript via Visual Intelligence (no API change).
    vi_plans = VisualIntelligenceService().plan_script(
        {
            "script_id": "demo-script",
            "teaching_sections": [
                {
                    "id": "vi-flow",
                    "title": "Login flow",
                    "narration": "The login process moves step by step through validation.",
                    "concept_tags": ["flow", "process", "step"],
                    "estimated_duration_sec": 5.0,
                }
            ],
        }
    )
    plans.extend(vi_plans)

    print("=" * 70)
    print("ExplainX — Asset Generation Demo")
    print("ScenePlan → AssetGenerationService → GeneratedAsset / ScenePackage")
    print("(local deterministic generators only — no cloud / no AI images)")
    print("=" * 70)

    for plan in plans:
        started = time.perf_counter()
        bundle = service.generate(
            plan,
            output_dir=OUT / "work",
            export_dir=OUT / "export",
            compose=True,
        )
        elapsed = time.perf_counter() - started
        print(f"\n── {plan.scene_id}")
        print(f"  visual type : {plan.intent.visual_type.value}")
        print(f"  generator   : {bundle.result.generator.value}")
        print(f"  cache       : {'HIT' if bundle.result.cache_hit else 'MISS'}")
        print(f"  time        : {elapsed:.3f}s (gen={bundle.result.generation_time_sec:.3f}s)")
        print(f"  primary     : {bundle.result.primary_path}")
        print(f"  composed    : {bundle.composed_path}")
        print(f"  export dir  : {bundle.export_dir}")

    # Second pass to demonstrate cache hits.
    print("\n── Cache replay")
    for plan in plans[:2]:
        bundle = service.generate(
            plan,
            output_dir=OUT / "work2",
            export_dir=OUT / "export2",
            compose=False,
        )
        print(f"  {plan.scene_id}: {'HIT' if bundle.result.cache_hit else 'MISS'}")

    print("\n" + "=" * 70)
    print(f"Outputs written under {OUT}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
