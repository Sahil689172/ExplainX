"""Smoke check for Phase 4.7 Asset Intelligence architecture (no inference)."""

from __future__ import annotations

from asset_intelligence import ConceptNode, RelationType
from asset_intelligence.container import build_default_services


def main() -> None:
    services = build_default_services()
    services.backend.initialize()

    sun = services.concept_graph.upsert_node(ConceptNode(name="Sun"))
    earth = services.concept_graph.upsert_node(ConceptNode(name="Earth"))
    services.concept_graph.add_relation(
        earth.concept_id, sun.concept_id, RelationType.ORBITS
    )

    plan = services.planner.plan_scene(
        scene_id="s1",
        concepts=[sun, earth],
        style_id="blueprint",
    )
    print("decisions:", [(d.requirement.concept.name, d.kind.value) for d in plan.decisions])

    style = services.styles.get("blueprint")
    bundles = list(services.prompts.generate_many(plan.decisions, style))
    print("prompt_count:", len(bundles))
    if bundles:
        print("sample_positive:", bundles[0].positive_prompt[:120])

    print("styles:", [s.style_id for s in services.styles.list_styles()])
    print("health:", services.backend.health())
    print("OK")


if __name__ == "__main__":
    main()
