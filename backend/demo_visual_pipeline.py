#!/usr/bin/env python
"""Demo: Script Generation → VisualIntelligenceService → ScenePlan → Timeline.

Runs the additive Visual Intelligence pipeline end-to-end *without* any LLM call
or image generation, and prints every generated ScenePlan in a readable format.

Usage::

    cd backend
    python demo_visual_pipeline.py            # built-in sample script
    python demo_visual_pipeline.py --timeline # also print Timeline scene JSON
    python demo_visual_pipeline.py --json      # dump raw JSON per plan

The sample script mimics the shape of an ``EducationalScript`` (topic-derived)
so the demo needs no database, network, or model weights.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from app.services.visual_intelligence import VisualIntelligenceService
from app.services.visual_intelligence.service import ScenePlan

# --------------------------------------------------------------------------- #
# A representative EducationalScript (topic input → teaching_sections).
# --------------------------------------------------------------------------- #
SAMPLE_SCRIPT: dict[str, Any] = {
    "script_id": "demo-script-001",
    "source_type": "topic",
    "learning_objectives": [
        "Understand how HTTP requests flow through a system",
        "Compare growth rates of common algorithms",
        "Recall the phases of the water cycle",
    ],
    "key_concepts": ["http", "algorithms", "water cycle"],
    "teaching_sections": [
        {
            "id": "scene-1",
            "title": "How an HTTP request flows",
            "narration": (
                "When you open a page, the browser sends a request to a server, "
                "which processes the steps in sequence and returns a response. "
                "This process follows a clear flow from client to server and back."
            ),
            "concept_tags": ["http", "request", "server", "flow", "process"],
            "estimated_duration_sec": 8.0,
        },
        {
            "id": "scene-2",
            "title": "Comparing algorithm growth",
            "narration": (
                "As input size grows, runtime increases. We compare linear versus "
                "quadratic growth on a chart to show how the curves diverge over time."
            ),
            "concept_tags": ["chart", "graph", "compare", "growth", "data"],
            "estimated_duration_sec": 7.5,
        },
        {
            "id": "scene-3",
            "title": "The water cycle",
            "narration": (
                "Water evaporates, condenses into clouds, and falls as rain. "
                "This cycle repeats continuously, moving through distinct stages."
            ),
            "concept_tags": ["cycle", "stages", "diagram", "process"],
            "estimated_duration_sec": 9.0,
        },
        {
            "id": "scene-4",
            "title": "A quick definition",
            "narration": "Latency is the time it takes for one request to complete.",
            "concept_tags": ["definition", "text"],
            "estimated_duration_sec": 4.0,
        },
    ],
}


def _print_plan(index: int, plan: ScenePlan) -> None:
    intent = plan.intent
    strategy = plan.strategy
    layered = plan.layered_scene
    fallbacks = ", ".join(r.value for r in strategy.fallback_renderers) or "—"
    layer_names = ", ".join(layer.layer_type.value for layer in layered.ordered())

    print(f"\n─── Scene {index}: {plan.scene_id} " + "─" * 30)
    print(f"  visual intent     : {intent.visual_type.value}")
    print(f"  confidence        : {intent.confidence:.2f}")
    print(f"  complexity        : {intent.complexity.value}")
    print(f"  estimated duration: {intent.estimated_duration:.2f}s")
    print(f"  primary renderer  : {strategy.primary_renderer.value}")
    print(f"  fallback renderers: {fallbacks}")
    print(f"  layers            : {layer_names}")
    print(f"  cache key         : {plan.cache_key[:32]}…")
    if intent.matched_keywords:
        print(f"  matched keywords  : {', '.join(intent.matched_keywords)}")
    print(f"  reasoning         : {intent.reasoning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visual Intelligence pipeline demo")
    parser.add_argument(
        "--json", action="store_true", help="print raw ScenePlan JSON for each scene"
    )
    parser.add_argument(
        "--timeline",
        action="store_true",
        help="also print the Timeline-Engine-ready scene JSON",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable DEBUG logging (shows intent/renderer/cache-key lines)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)-7s | %(name)s | %(message)s",
    )

    service = VisualIntelligenceService()

    print("=" * 70)
    print("ExplainX — Visual Intelligence Pipeline Demo")
    print("Script Generation → VisualIntelligenceService → ScenePlan → Timeline")
    print("(no LLM calls, no image generation)")
    print("=" * 70)
    print(f"Script: {SAMPLE_SCRIPT['script_id']} "
          f"({len(SAMPLE_SCRIPT['teaching_sections'])} teaching sections)")

    plans = service.plan_script(SAMPLE_SCRIPT)

    for i, plan in enumerate(plans, start=1):
        _print_plan(i, plan)
        if args.json:
            print("  raw plan:")
            print(json.dumps(plan.to_dict(), indent=2))
        if args.timeline:
            print("  timeline scene:")
            print(json.dumps(plan.to_timeline_scene(), indent=2))

    print("\n" + "=" * 70)
    print(f"Generated {len(plans)} ScenePlan(s).")
    renderers = {p.strategy.primary_renderer.value for p in plans}
    print(f"Renderers selected: {', '.join(sorted(renderers))}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
