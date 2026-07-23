"""Regression: quality and generation packages must not circular-import."""

from __future__ import annotations

from pathlib import Path


def test_quality_repair_has_no_section_generation_import() -> None:
    import app.features.quality.repair as repair_mod

    source = Path(repair_mod.__file__).read_text(encoding="utf-8")
    assert "section_generation" not in source
    assert "single_script" not in source
    assert repair_mod.ScriptRepairService is not None


def test_narration_service_has_no_quality_import() -> None:
    import app.features.narration.service as narration_svc

    source = Path(narration_svc.__file__).read_text(encoding="utf-8")
    assert "app.features.quality" not in source


def test_scene_builder_has_no_quality_or_ollama_import() -> None:
    import app.features.scene_builder.builder as builder_mod

    source = Path(builder_mod.__file__).read_text(encoding="utf-8")
    assert "app.features.quality" not in source
    # Metadata may mention the string key "ollama_model"; forbid import lines only.
    import_lines = [
        line
        for line in source.splitlines()
        if line.lstrip().startswith(("import ", "from "))
    ]
    assert all("ollama" not in line for line in import_lines)


def test_section_generation_service_has_no_quality_import() -> None:
    import app.features.section_generation.service as section_svc

    source = Path(section_svc.__file__).read_text(encoding="utf-8")
    assert "app.features.quality" not in source


def test_cross_import_order_both_directions() -> None:
    from app.features.narration import service as narration_a
    from app.features.quality import repair as repair_a
    from app.features.scene_builder import builder as builder_a

    assert repair_a.ScriptRepairService is not None
    assert narration_a.NarrationGenerationService is not None
    assert builder_a.SceneBuilder is not None


def test_content_intelligence_wires_narration_and_qa() -> None:
    from app.core.config import get_settings
    from app.db import session as db_session
    from app.features.narration.service import NarrationGenerationService
    from app.features.quality.service import QualityAssuranceService
    from app.features.script.service import ContentIntelligenceService

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    with db_session.SessionLocal() as session:
        service = ContentIntelligenceService(session, get_settings())
        assert isinstance(service._narration_service, NarrationGenerationService)
        assert isinstance(service._quality_service, QualityAssuranceService)


def test_application_starts() -> None:
    from app.features.narration.service import NarrationGenerationService
    from app.features.quality.service import QualityAssuranceService
    from app.features.script.service import ContentIntelligenceService
    from app.features.scene_builder.builder import SceneBuilder
    from app.main import create_app

    app = create_app()
    assert app.title
    assert QualityAssuranceService is not None
    assert NarrationGenerationService is not None
    assert SceneBuilder is not None
    assert ContentIntelligenceService is not None
