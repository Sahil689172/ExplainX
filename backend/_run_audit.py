"""Offline audit runner — writes results to _audit_out.txt."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_audit_out.txt"


def main() -> int:
    lines: list[str] = []
    # Import smoke
    try:
        sys.path.insert(0, str(ROOT))
        from app.features.quality.repair import ScriptRepairService
        from app.features.quality.service import QualityAssuranceService
        from app.features.script.service import ContentIntelligenceService
        from app.features.section_generation.service import SectionGenerationService
        from app.features.single_script.service import SingleScriptGenerationService
        from app.main import create_app

        app = create_app()
        lines.append(
            f"IMPORT_OK {app.title} "
            f"{ScriptRepairService.__name__} "
            f"{SectionGenerationService.__name__} "
            f"{SingleScriptGenerationService.__name__} "
            f"{QualityAssuranceService.__name__} "
            f"{ContentIntelligenceService.__name__}"
        )
    except Exception as exc:  # noqa: BLE001
        lines.append(f"IMPORT_FAIL {type(exc).__name__}: {exc}")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_circular_imports.py",
        "tests/test_prompt_template_format.py",
        "tests/test_section_generation.py",
        "tests/test_single_script_generation.py",
        "tests/test_quality_assurance.py",
        "tests/test_teaching_outline.py",
        "tests/test_script_generation.py",
        "tests/test_phase36_script_standardization.py",
        "tests/test_phase3_content_intelligence.py",
        "tests/test_pipeline_timing.py",
        "-q",
        "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines.append(proc.stdout or "")
    lines.append(proc.stderr or "")
    lines.append(f"EXIT:{proc.returncode}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
