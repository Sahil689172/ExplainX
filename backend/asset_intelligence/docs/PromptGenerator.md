# Prompt Generator

**Schema version:** `1.0.0`  
**Modules:** `prompt_generator`, `schemas.prompt`

## Responsibility

Produce `PromptBundle` objects **only for assets the planner marked GENERATE**.

It does **not** receive scenes. Pipeline:

```text
Scene → Concepts → Asset Planner → Prompt Generator
```

## WHAT vs HOW

```text
WHAT  = educational subject clause from concept / ontology
HOW   = style profile positive/negative prompts + palette rules
```

Example:

```text
WHAT: educational illustration of Earth, category planet, front view
HOW:  blueprint style positive_prompt from blueprint.json
→ positive_prompt = WHAT + ", " + HOW
```

## Contract

`PromptGeneratorProtocol`:

- `generate(decision, style) → PromptBundle` — raises if not `GENERATE`
- `generate_many(decisions, style) →` filters to GENERATE only

## Output: `PromptBundle`

| Field | Notes |
|-------|-------|
| `requirement` | Original planner requirement |
| `style` | Full `StyleProfile` snapshot |
| `positive_prompt` / `negative_prompt` | Assembled text |
| `prompt_id` | UUID |
| `width` / `height` | Defaults 512 (processor-aligned) |
| `metadata.what` / `how_style_id` | Explicit separation for debugging |

Downstream, `GenerationRequest` wraps a bundle for `ImageBackend.generate`.

## Non-goals (Phase 4.7)

- No LLM rewriting
- No model-specific token packing
- No Stable Diffusion / Flux parameter tuning beyond schema placeholders
