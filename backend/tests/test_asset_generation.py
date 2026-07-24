"""Tests for the Asset Generation Engine (ScenePlan → GeneratedAsset)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.asset_generation import (
    GENERATOR_PRIORITY,
    AssetGenerationCache,
    AssetGenerationService,
    AssetStatus,
    AssetValidator,
    GeneratorType,
    compute_plan_hash,
    default_registry,
)
from app.services.asset_generation.generators import (
    BackgroundGenerator,
    IconGenerator,
    InfographicGenerator,
    LocalImageGenerator,
    MatplotlibGenerator,
    MermaidGenerator,
    SVGGenerator,
    TimelineGenerator,
)
from app.services.visual_intelligence.schemas import (
    Complexity,
    LayerType,
    RendererType,
    RenderingStrategy,
    VisualIntent,
    VisualType,
)
from app.services.visual_intelligence.service import ScenePlan
from app.services.visual_intelligence.layers import LayeredScene, VisualLayer


def _plan(
    *,
    scene_id: str,
    visual_type: VisualType,
    renderer: RendererType,
    keywords: list[str] | None = None,
) -> ScenePlan:
    intent = VisualIntent(
        scene_id=scene_id,
        visual_type=visual_type,
        confidence=0.8,
        reasoning=f"Test plan for {visual_type.value}",
        suggested_renderer=renderer,
        estimated_duration=5.0,
        complexity=Complexity.SIMPLE,
        matched_keywords=keywords or [visual_type.value, "process", "step"],
    )
    strategy = RenderingStrategy(
        scene_id=scene_id,
        visual_type=visual_type,
        primary_renderer=renderer,
        layers=[LayerType.BACKGROUND, LayerType.DIAGRAM],
    )
    layered = LayeredScene(
        scene_id=scene_id,
        duration_sec=5.0,
        layers=[
            VisualLayer(layer_type=LayerType.BACKGROUND, z_index=0),
            VisualLayer(layer_type=LayerType.DIAGRAM, z_index=20, renderer=renderer),
        ],
    )
    return ScenePlan(
        scene_id=scene_id,
        intent=intent,
        strategy=strategy,
        layered_scene=layered,
        cache_key="test",
    )


def test_registry_registers_and_selects() -> None:
    registry = default_registry()
    names = {g.generator_type() for g in registry.all()}
    assert GeneratorType.MERMAID in names
    assert GeneratorType.LOCAL_IMAGE in names
    plan = _plan(
        scene_id="flow-1",
        visual_type=VisualType.FLOWCHART,
        renderer=RendererType.MERMAID,
    )
    selected = registry.select(plan)
    assert selected is not None
    assert selected.generator_type() == GeneratorType.MERMAID


def test_registry_priority_order() -> None:
    assert GENERATOR_PRIORITY[0] == GeneratorType.MERMAID
    assert GENERATOR_PRIORITY[-1] == GeneratorType.LOCAL_IMAGE


def test_cache_roundtrip(tmp_path: Path) -> None:
    digest = compute_plan_hash(
        scene_id="s1",
        visual_type="chart",
        renderer="matplotlib",
        style="educational",
        theme="light",
        language="en",
    )
    assert len(digest) == 64
    cache = AssetGenerationCache(tmp_path / "cache")
    assert cache.lookup(digest) is None


def test_mermaid_generator(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="http-flow",
        visual_type=VisualType.FLOWCHART,
        renderer=RendererType.MERMAID,
        keywords=["request", "server", "response"],
    )
    result = MermaidGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED
    assert any(a.path.endswith(".mmd") for a in result.assets)
    assert Path(result.primary_path).is_file()


def test_svg_generator(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="geo-diagram",
        visual_type=VisualType.DIAGRAM,
        renderer=RendererType.SVG,
        keywords=["cycle", "stages"],
    )
    result = SVGGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED
    assert any(a.path.endswith(".svg") for a in result.assets)


def test_matplotlib_generator(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    plan = _plan(
        scene_id="growth-chart",
        visual_type=VisualType.CHART,
        renderer=RendererType.MATPLOTLIB,
        keywords=["chart", "growth", "line"],
    )
    result = MatplotlibGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED
    assert Path(result.primary_path).is_file()


def test_icon_generator(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="icons",
        visual_type=VisualType.ICON,
        renderer=RendererType.ICON,
        keywords=["idea", "book"],
    )
    result = IconGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED


def test_background_generator(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="bg",
        visual_type=VisualType.BACKGROUND,
        renderer=RendererType.BACKGROUND,
        keywords=["grid"],
    )
    result = BackgroundGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED


def test_timeline_generator(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="history",
        visual_type=VisualType.TIMELINE,
        renderer=RendererType.SVG,
        keywords=["era", "event"],
    )
    result = TimelineGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED


def test_infographic_generator(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="mixed-info",
        visual_type=VisualType.MIXED,
        renderer=RendererType.SVG,
        keywords=["a", "b", "c"],
    )
    result = InfographicGenerator().generate(plan, tmp_path)
    assert result.status == AssetStatus.GENERATED


def test_local_image_generator_is_interface_only(tmp_path: Path) -> None:
    plan = _plan(
        scene_id="photo",
        visual_type=VisualType.PHOTO,
        renderer=RendererType.OPENVINO,
    )
    gen = LocalImageGenerator()
    assert gen.supports(plan)
    result = gen.generate(plan, tmp_path)
    assert result.status == AssetStatus.SKIPPED
    assert result.assets == []


def test_validator_rejects_missing(tmp_path: Path) -> None:
    from app.services.asset_generation.models import (
        AssetFormat,
        AssetType,
        GeneratedAsset,
        GenerationResult,
        GeneratorType,
    )

    result = GenerationResult(
        scene_id="bad",
        generator=GeneratorType.SVG,
        status=AssetStatus.GENERATED,
        assets=[
            GeneratedAsset(
                asset_id="1",
                scene_id="bad",
                asset_type=AssetType.DIAGRAM,
                format=AssetFormat.PNG,
                path=str(tmp_path / "missing.png"),
                generator=GeneratorType.SVG,
            )
        ],
        primary_path=str(tmp_path / "missing.png"),
    )
    with pytest.raises(Exception):
        AssetValidator().validate_result(result)


def test_service_generate_and_cache(tmp_path: Path) -> None:
    service = AssetGenerationService.with_cache(tmp_path / "cache")
    plan = _plan(
        scene_id="svc-flow",
        visual_type=VisualType.FLOWCHART,
        renderer=RendererType.MERMAID,
        keywords=["process", "steps"],
    )
    first = service.generate(plan, output_dir=tmp_path / "out", export_dir=tmp_path / "export")
    assert first.result.status in {AssetStatus.GENERATED, AssetStatus.CACHED}
    assert first.composed_path and Path(first.composed_path).is_file()
    second = service.generate(plan, output_dir=tmp_path / "out2", export_dir=tmp_path / "export2")
    assert second.result.cache_hit is True


def test_scene_composer_builds_package(tmp_path: Path) -> None:
    service = AssetGenerationService()
    plan = _plan(
        scene_id="compose-me",
        visual_type=VisualType.CHART,
        renderer=RendererType.MATPLOTLIB,
        keywords=["chart", "data"],
    )
    bundle = service.generate(plan, output_dir=tmp_path / "out", compose=True)
    package = service.compose_bundle(bundle)
    assert package.composed_path
    assert Path(package.composed_path).is_file()


def test_integration_with_visual_intelligence_plan_script(tmp_path: Path) -> None:
    from app.services.visual_intelligence import VisualIntelligenceService

    script = {
        "script_id": "demo",
        "teaching_sections": [
            {
                "id": "s1",
                "title": "HTTP request flow",
                "narration": "A request travels step by step from client to server.",
                "concept_tags": ["flow", "process", "request"],
                "estimated_duration_sec": 6.0,
            },
            {
                "id": "s2",
                "title": "Growth chart",
                "narration": "We compare growth on a chart over time.",
                "concept_tags": ["chart", "graph", "data"],
                "estimated_duration_sec": 6.0,
            },
        ],
    }
    plans = VisualIntelligenceService().plan_script(script)
    service = AssetGenerationService.with_cache(tmp_path / "cache")
    bundles = service.generate_many(plans, output_dir=tmp_path / "gen", export_dir=tmp_path / "exp")
    assert len(bundles) == 2
    for bundle in bundles:
        assert bundle.result.primary_path
        assert Path(bundle.result.primary_path).is_file()
