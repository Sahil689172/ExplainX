# Visual Intelligence — Architecture

Hybrid educational visual generation: decide **what** visual each scene needs,
**which** renderer should produce it, cache the result for reuse, and model
**multi-layer** scene composition. This module is **additive** — it does not
modify any completed phase, the rendering engine, or the Timeline Engine, and
it does not call an LLM.

```
Scene data
    │
    ▼
VisualIntentAnalyzer ─────────► VisualIntent
 (deterministic, rule-based)     (visual_type, confidence, reasoning,
    │                             suggested_renderer, estimated_duration,
    │                             complexity)
    ▼
VisualAssetRouter ────────────► RenderingStrategy
 (configurable, never renders)   (primary + fallback renderers, options,
    │                             layers, cost/time estimates)
    ▼
LayeredSceneComposer ─────────► LayeredScene
 (additive, backward-compat)     (Background/Foreground/Diagram/Overlay/
    │                             Labels/Icons/Effects, per-layer animation)
    ▼
RendererRegistry  ◄── plugin plugins declare capability only
    │
    ▼
AssetCache / AssetRepository ─► reuse by SHA256(prompt, model, params,
                                 renderer, seed)
```

## Components

### 1. `VisualIntentAnalyzer` (`intent_analyzer.py`)
Deterministic, keyword-driven classifier. No LLM. Produces a `VisualIntent`
with `visual_type`, `confidence`, `reasoning`, `suggested_renderer`,
`estimated_duration`, and `complexity`. Rules are data (`VisualRule`) and can be
overridden by passing a custom `rules` tuple.

Supported visual types: `DIAGRAM, FLOWCHART, TIMELINE, CHART, TABLE, MAP,
MATHEMATICAL, SCIENTIFIC, ILLUSTRATION, PHOTO, ICON, BACKGROUND, TEXT_ONLY,
MIXED`.

Prompt templates for a **future** LLM classifier are in `prompt_templates.py`.
They target the exact `VisualIntent` JSON shape so the swap is drop-in. They are
never invoked today.

### 2. `VisualAssetRouter` (`asset_router.py`)
Maps `VisualIntent → RenderingStrategy`. **Never generates assets** — it only
plans. Selection order:

1. `RouterConfig.overrides[visual_type]` (hard override)
2. Cheapest **capable** registered renderer (honouring the analyzer's
   suggestion when valid), with `preference_order` as a tiebreaker
3. Analyzer suggestion when nothing is registered for the type

Fully configurable via `RouterConfig`: overrides, preference order, per-renderer
options, default layers, and `max_fallbacks`.

### 3. Renderer plugins (`renderers/`)
Plugin-based. Each plugin implements the same contract and **knows nothing about
other plugins**:

| Method | Purpose |
|--------|---------|
| `supports(intent)` | can it produce this visual type? |
| `render(request)` | uniform seam; uses a **bound** backend, else no-op |
| `estimate_cost(intent)` | relative cost, scaled by complexity |
| `estimate_time(intent)` | wall-clock seconds estimate |
| `metadata()` | static descriptor for discovery/docs |

Plugins declare capability only; they contain **no rendering logic** and never
replace the existing engines. `RendererRegistry` is the sole component aware of
the full set; add renderers with `registry.register(plugin)`.

Standard plugins: `Mermaid, SVG, Matplotlib, Manim, OpenVINO, Icon, Background`.

### 4. Asset Cache + Repository (`cache.py`, `repository.py`)
Content-addressed reuse. The cache key is
`SHA256(prompt, model, parameters, renderer, seed)` via
`RenderRequest.canonical()` (order-independent JSON).

- Identical request → cached `AssetRecord` returned.
- New request → caller-produced asset stored, then returned.

Each entry stores: PNG, optional SVG, JSON metadata sidecar, thumbnail,
`created_at`, `renderer`, and `generation_time_sec`. `AssetRepository` adds
`find/exists/register/list/stats`. Neither renders; `get_or_create(request,
producer)` is the only generation seam and delegates production to the caller.

### 5. Multi-layer composition (`layers.py`)
`LayeredScene` holds ordered `VisualLayer`s (Background, Foreground, Diagram,
Overlay, Labels, Icons, Effects), each with an independent `LayerAnimation`
(metadata only — the Timeline Engine is untouched). Backward compatibility:

- `LayeredScene.from_single_asset(...)` reproduces legacy single-image scenes.
- `LayeredScene.to_legacy_dict()` exposes `illustration_path` so existing
  downstream code keeps working unchanged.

## Pipeline integration

`VisualIntelligenceService` is the façade:

```python
from app.services.visual_intelligence import VisualIntelligenceService, SceneInput

service = VisualIntelligenceService.with_cache("cache/visual_intelligence")
plan = service.plan_scene(SceneInput(
    scene_id="scene_01",
    title="The Water Cycle",
    narration="Water evaporates, condenses into clouds, then precipitates...",
    keywords=["process", "cycle"],
    educational_concepts=["evaporation", "condensation"],
    learning_objective="Explain the stages of the water cycle",
))

plan.intent.visual_type       # VisualType.FLOWCHART
plan.strategy.primary_renderer  # RendererType.MERMAID
plan.layered_scene.to_legacy_dict()  # consumable by the existing pipeline
```

Because `to_legacy_dict()` yields `illustration_path`, an existing scene
composer can adopt the plan without code changes; richer consumers can read the
full `layers` array.

## Guarantees / constraints honoured

- **No completed phase modified.** New package under `app/services/`.
- **Rendering engine untouched.** Plugins are capability descriptors; the cache
  never renders.
- **Timeline Engine untouched.** Layer animation is advisory metadata.
- **No LLM called.** Classification is rule-based; prompts are staged for later.
- **Backward compatible.** Legacy single-image flow reproducible and emitted.

## Extending

- **New renderer:** implement `RendererPlugin`, then `registry.register(...)`.
- **New rule:** add a `VisualRule` or pass a custom `rules` tuple to the analyzer.
- **Custom routing:** construct `RouterConfig(overrides=..., preference_order=...)`.
- **LLM upgrade:** implement an analyzer that fills `VisualIntent` using
  `prompt_templates.build_classification_prompt(...)`; the rest is unchanged.
