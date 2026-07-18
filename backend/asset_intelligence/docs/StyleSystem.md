# Style System

**Schema version:** `1.0.0`  
**Modules:** `style_system`, `schemas.style`

## Rule

**Style is NEVER hardcoded into prompts in Python.**  
Styles live as independent JSON profiles under `style_system/styles/`.

## Separation: WHAT vs HOW

| Layer | Owns |
|-------|------|
| Concept / Ontology | **WHAT** — Earth, Neuron, Battery |
| Style profile | **HOW** — blueprint lines, chalkboard chalk, flat fills |

Prompt Generator concatenates WHAT + HOW only for missing assets.

## Profile fields

Each `*.json` maps to `StyleProfile`:

| Field | Role |
|-------|------|
| `style_id` | Stable ID (`flat`, `blueprint`, …) |
| `positive_prompt` / `negative_prompt` | HOW clauses |
| `color_palette` | Hex colors |
| `line_weight` | thin \| medium \| bold |
| `lighting` | e.g. flat, soft cel |
| `background_rules` | Alpha / solid policy |
| `renderer_preferences` | Hints for Asset Processor / Renderer |
| `lora_mapping` | Future LoRA IDs (empty in 4.7) |
| `controlnet_mapping` | Future ControlNet hints (empty in 4.7) |

## Bundled profiles

```text
styles/
  flat.json
  blueprint.json
  chalkboard.json
  whiteboard.json
  cartoon.json
  minimal_vector.json
```

## Loader

`StyleSystem` loads all `*.json` on init / `reload()` and implements `StyleSystemProtocol`.

## Extension points

1. Drop a new JSON file — no code change required for discovery.
2. Fill `lora_mapping` / `controlnet_mapping` when backends land.
3. Style Cache invalidates independently of Asset / Prompt caches.
