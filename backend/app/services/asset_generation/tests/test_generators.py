"""Package-local unit smoke for asset generators (also covered by tests/test_asset_generation.py)."""

from __future__ import annotations

from pathlib import Path

from app.services.asset_generation.generators.mermaid_generator import MermaidGenerator
from app.services.asset_generation.models import AssetStatus
from app.services.asset_generation.registry import default_registry
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


def _plan() -> ScenePlan:
    intent = VisualIntent(
        scene_id="pkg-flow",
        visual_type=VisualType.FLOWCHART,
        confidence=0.7,
        reasoning="flow",
        suggested_renderer=RendererType.MERMAID,
        estimated_duration=4.0,
        complexity=Complexity.SIMPLE,
        matched_keywords=["process", "steps"],
    )
    strategy = RenderingStrategy(
        scene_id="pkg-flow",
        visual_type=VisualType.FLOWCHART,
        primary_renderer=RendererType.MERMAID,
        layers=[LayerType.DIAGRAM],
    )
    layered = LayeredScene(
        scene_id="pkg-flow",
        layers=[VisualLayer(layer_type=LayerType.DIAGRAM, z_index=20)],
    )
    return ScenePlan(
        scene_id="pkg-flow",
        intent=intent,
        strategy=strategy,
        layered_scene=layered,
    )


def test_default_registry_nonempty() -> None:
    assert len(default_registry().all()) >= 7


def test_mermaid_writes_files(tmp_path: Path) -> None:
    result = MermaidGenerator().generate(_plan(), tmp_path)
    assert result.status == AssetStatus.GENERATED
    assert Path(result.primary_path).is_file()
