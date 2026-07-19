# Phase 5.6 — Prompt Intelligence Engine

Transforms short user prompts into high-quality educational generation prompts
**before** Asset Manager / cache / OpenVINO.

```text
User Prompt
      │
      ▼
Prompt Intelligence Engine
      │
      ▼
Enhanced Prompt (+ negative prompt + metadata)
      │
      ▼
Asset Manager  (PromptEnhancer adapter — no AssetManager code changes)
      │
Cache / Repository
      │
OpenVINO
```

## Package

```text
backend/image_generation/prompt_intelligence/
  prompt_engine.py          # PromptEngine, RuleBasedPromptEngine, LLMPromptEngine
  prompt_templates.py       # Per-subject templates + universal rules
  subject_classifier.py     # Rule-based subject detection
  style_profiles.py         # Flat Vector (default), Diagram, Icon, …
  prompt_validator.py
  negative_prompt_builder.py
  prompt_metadata.py
```

## Interfaces (LLM-ready)

- `PromptEngine` — abstract
- `RuleBasedPromptEngine` — Phase 5.6 default
- `LLMPromptEngine` — placeholder (falls back to rules)

```python
from image_generation.prompt_enhancer import PromptEnhancer
from image_generation.prompt_intelligence import LLMPromptEngine, RuleBasedPromptEngine

# Default (automatic via PromptEnhancer):
PromptEnhancer()

# Explicit / future LLM:
PromptEnhancer(engine=LLMPromptEngine())
```

## Metadata

`PromptIntelligenceResult` stores `original_prompt`, `enhanced_prompt`, `subject`,
`style`, `negative_prompt`, `template_used`, `confidence`, scores, and keywords.

`PromptEnhancer.enhance()` returns the AssetManager-compatible dict plus extra keys
(`negative_prompt`, `keywords`, `subject`, `confidence`, …).

## Logging

`PROMPT_RECEIVED` → `PROMPT_VALIDATED` → `SUBJECT_CLASSIFIED` → `STYLE_SELECTED`
→ `NEGATIVE_PROMPT_CREATED` → `PROMPT_ENHANCED`

## Tests

```bash
cd backend
python test_prompt_engine.py
python -m unittest image_generation.tests.test_prompt_intelligence_unit
```

## Non-goals

Does **not** modify OpenVINO backend, Asset Repository, Asset Manager, or Smart Cache.
Integration is via existing `PromptEnhancer` / `enhancer=` dependency injection.
