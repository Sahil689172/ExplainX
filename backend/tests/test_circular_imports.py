"""Regression: quality / generation packages must not circular-import."""

from __future__ import annotations

from pathlib import Path


def test_quality_repair_has_no_section_generation_import() -> None:
    import app.features.quality.repair as repair_mod

    source = Path(repair_mod.__file__).read_text(encoding="utf-8")
    assert "section_generation" not in source
    assert "single_script" not in source
    assert repair_mod.ScriptRepairService is not None


def test_section_generation_service_has_no_quality_import() -> None:
    import app.features.section_generation.service as section_svc

    source = Path(section_svc.__file__).read_text(encoding="utf-8")
    assert "app.features.quality" not in source


def test_single_script_service_has_no_quality_import() -> None:
    import app.features.single_script.service as single_svc

    source = Path(single_svc.__file__).read_text(encoding="utf-8")
    assert "app.features.quality" not in source


def test_cross_import_order_both_directions() -> None:
    """Import in either order must succeed (the original cycle failed here)."""
    from app.features.quality import repair as repair_a
    from app.features.section_generation import service as section_a
    from app.features.single_script import service as single_a

    assert repair_a.ScriptRepairService is not None
    assert section_a.SectionGenerationService is not None
    assert single_a.SingleScriptGenerationService is not None

    from app.features.quality.repair import ScriptRepairService
    from app.features.section_generation.service import SectionGenerationService
    from app.features.single_script.service import SingleScriptGenerationService

    assert SectionGenerationService is section_a.SectionGenerationService
    assert SingleScriptGenerationService is single_a.SingleScriptGenerationService
    assert ScriptRepairService is repair_a.ScriptRepairService


def test_content_intelligence_wires_single_script_and_qa() -> None:
    from app.core.config import get_settings
    from app.db import session as db_session
    from app.features.quality.service import QualityAssuranceService
    from app.features.script.service import ContentIntelligenceService
    from app.features.single_script.service import SingleScriptGenerationService

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    with db_session.SessionLocal() as session:
        service = ContentIntelligenceService(session, get_settings())
        assert isinstance(
            service._single_script_service, SingleScriptGenerationService
        )
        assert isinstance(service._quality_service, QualityAssuranceService)


def test_application_starts() -> None:
    from app.features.quality.service import QualityAssuranceService
    from app.features.script.service import ContentIntelligenceService
    from app.features.section_generation.service import SectionGenerationService
    from app.features.single_script.service import SingleScriptGenerationService
    from app.main import create_app

    app = create_app()
    assert app.title
    assert QualityAssuranceService is not None
    assert SectionGenerationService is not None
    assert SingleScriptGenerationService is not None
    assert ContentIntelligenceService is not None
