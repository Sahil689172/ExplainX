"""
Phase 5.6 — Prompt Intelligence Engine smoke / verification.

Run from backend/:

    python test_prompt_engine.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from image_generation.prompt_enhancer import PromptEnhancer
from image_generation.prompt_intelligence import RuleBasedPromptEngine
from image_generation.prompt_intelligence.negative_prompt_builder import NEGATIVE_TERMS


CASES: tuple[tuple[str, str, str], ...] = (
    ("Earth", "Geography", "geography_v1"),
    ("Heart", "Biology", "biology_v1"),
    ("DNA", "Biology", "biology_v1"),
    ("Volcano", "Geography", "geography_v1"),
    ("Computer Motherboard", "Computer Science", "cs_v1"),
    ("Photosynthesis", "Biology", "biology_v1"),
    ("Sorting Algorithm", "Computer Science", "cs_v1"),
    ("Newton's Laws", "Physics", "physics_v1"),
)


def main() -> int:
    engine = RuleBasedPromptEngine()
    enhancer = PromptEnhancer(engine=engine)
    failed = 0

    print("=" * 60)
    print("Phase 5.6 — Prompt Intelligence Engine")
    print("=" * 60)

    for prompt, expect_subject, expect_template in CASES:
        result = engine.enhance(prompt)
        adapter = enhancer.enhance(prompt)
        print()
        print(f"INPUT: {prompt!r}")
        print(f"  subject:   {result.subject} (expect {expect_subject})")
        print(f"  template:  {result.template_used} (expect {expect_template})")
        print(f"  style:     {result.style} / {result.style_id}")
        print(f"  confidence:{result.confidence:.3f}")
        print(f"  scores:    {result.scores.to_dict()}")
        print(f"  enhanced:  {result.enhanced_prompt[:120]}...")
        print(f"  negative:  {result.negative_prompt[:80]}...")

        checks = [
            (result.subject == expect_subject, "subject"),
            (result.template_used == expect_template, "template"),
            (result.style_id == "flat_vector", "default_style"),
            (all(t in result.negative_prompt for t in ("no text", "no watermark")), "negative"),
            (result.validated is True, "validated"),
            ("educational" in result.enhanced_prompt.lower(), "educational_clause"),
            (adapter["category"] == expect_subject, "adapter_category"),
            (adapter["title"], "adapter_title"),
        ]
        for ok, name in checks:
            if not ok:
                print(f"  FAIL: {name}")
                failed += 1
            else:
                print(f"  OK: {name}")

    # Ensure full negative term list is present
    neg = engine.enhance("Earth").negative_prompt
    missing = [t for t in NEGATIVE_TERMS if t not in neg]
    if missing:
        print(f"\nFAIL: missing negative terms: {missing}")
        failed += 1
    else:
        print("\nOK: full negative prompt term list")

    # LLM placeholder still returns a result
    from image_generation.prompt_intelligence import LLMPromptEngine

    llm = LLMPromptEngine().enhance("Earth")
    assert llm.subject == "Geography"
    print("OK: LLMPromptEngine placeholder falls back to rules")

    print()
    if failed:
        print(f"RESULT: {failed} check(s) failed")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
