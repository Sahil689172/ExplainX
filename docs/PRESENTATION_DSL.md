# ExplainX — Presentation DSL Specification

**Document Status:** Canonical Language Specification  
**DSL Version Defined Herein:** `1.0`  
**Document Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Companions:** [`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) · [`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md)  

> **Authority:** The Presentation DSL is the **official language of ExplainX**.  
> Agents plan and compile into it. Engines animate and render from it.  
> The renderer **never** calls AI agents. If a feature cannot be expressed in the DSL (or a versioned extension), it cannot be rendered.

---

## Table of Contents

1. [Why a Presentation DSL Exists](#1-why-a-presentation-dsl-exists)
2. [Design Goals & Non-Goals](#2-design-goals--non-goals)
3. [Document Model Overview](#3-document-model-overview)
4. [Root Object: Project](#4-root-object-project)
5. [Metadata](#5-metadata)
6. [Theme](#6-theme)
7. [Assets](#7-assets)
8. [Voice](#8-voice)
9. [Subtitles](#9-subtitles)
10. [Layout System](#10-layout-system)
11. [Scene](#11-scene)
12. [Background](#12-background)
13. [Objects (Scene Elements)](#13-objects-scene-elements)
14. [Object Kind Catalog](#14-object-kind-catalog)
15. [Animations](#15-animations)
16. [Camera](#16-camera)
17. [Timeline](#17-timeline)
18. [Duration Model](#18-duration-model)
19. [Coordinate, Color & Style Systems](#19-coordinate-color--style-systems)
20. [Validation Rules](#20-validation-rules)
21. [Versioning](#21-versioning)
22. [Extensibility & Plugins](#22-extensibility--plugins)
23. [How Agents Read and Write the DSL](#23-how-agents-read-and-write-the-dsl)
24. [Renderer Contract](#24-renderer-contract)
25. [Worked Examples](#25-worked-examples)
26. [Anti-Patterns](#26-anti-patterns)
27. [Normative Glossary](#27-normative-glossary)
28. [Appendix: Complete Field Index](#28-appendix-complete-field-index)

---

## 1. Why a Presentation DSL Exists

ExplainX is not a prompt-to-pixels video generator. It is an **AI Presentation Engine**. Between “understanding a document” and “writing an MP4” there must be a stable, inspectable, versioned intermediate language.

Without a DSL:

- Every agent would invent its own ad-hoc structure  
- The renderer would need to call LLMs mid-frame  
- Theme changes would require regenerating pedagogy  
- Testing would require expensive model calls  
- Offline resume/cache would be unreliable  
- Plugins could not extend visuals safely  

With a Presentation DSL:

```
Document → Knowledge → Plans → Presentation DSL → Scene Graph → Timeline → Renderer → MP4
```

The DSL is:

| Property | Meaning |
|----------|---------|
| **Central** | Visual, motion, voice sync, and render all hang off it |
| **Typed** | Every field has meaning and validation |
| **Deterministic downstream** | Same DSL + same engines ⇒ same video (modulo encoder nondeterminism policy) |
| **Auditable** | Diffable JSON for debugging teaching structure |
| **Extensible** | Plugins add kinds/fields under version gates |

### 1.1 Constitutional Rule

```
RULE: The Presentation DSL is the only visual/motion contract the renderer understands.
RULE: The renderer consumes DSL (+ compiled timeline + media paths). It never talks to AI agents.
RULE: Agents may write or refine DSL artifacts; they must not mutate another agent's output in place.
```

---

## 2. Design Goals & Non-Goals

### 2.1 Goals

1. Express educational scenes as **diagram primitives**, not freeform video clips  
2. Separate **semantics** (`kind` + `props`) from **skin** (`theme` + `style_tokens`)  
3. Support narration sync via IDs and duration bindings  
4. Remain readable by humans debugging a failed job  
5. Allow partial compilation (plans → DSL draft → enriched DSL)  
6. Enable caching and incremental rebuilds  

### 2.2 Non-Goals (DSL v1.0)

1. Being a full After Effects / SVG animation language  
2. Embedding raw LLM prompts inside scenes  
3. Requiring generative images for every scene  
4. Interactive runtime presentation UI (V1 product hides the deck)  
5. Pixel-perfect authoring for human designers (machine-authored first)

---

## 3. Document Model Overview

### 3.1 Single-File Conceptual Shape

A Presentation DSL document is a JSON object:

```json
{
  "dsl_version": "1.0",
  "project": { },
  "metadata": { },
  "theme": { },
  "assets": [ ],
  "voice": { },
  "subtitles": { },
  "layout_defaults": { },
  "scenes": [ ],
  "timeline": { },
  "extensions": { }
}
```

### 3.2 Object Graph

```
Project
├── Metadata
├── Theme
├── Assets[]
├── Voice
├── Subtitles
├── LayoutDefaults
├── Scenes[]
│   ├── Background
│   ├── Layout
│   ├── Objects[]
│   ├── Animations[]
│   ├── Camera
│   ├── VoiceBinding
│   ├── SubtitleBinding
│   └── Duration
└── Timeline
    ├── Tracks[]
    ├── Markers[]
    └── TotalDuration
```

### 3.3 ID Rules

| Rule | Statement |
|------|-----------|
| I1 | All IDs are strings matching `^[a-z][a-z0-9_]*$` unless noted |
| I2 | IDs are unique within their scope (project-global for scenes/assets; scene-local for objects) |
| I3 | References use IDs only — never positional array indices as identity |
| I4 | Deleted objects leave no dangling references (validator enforces) |

---

## 4. Root Object: Project

The `project` object identifies the presentation instance and compile context.

### 4.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` (UUID) | yes | Stable project identifier |
| `title` | `string` | yes | Human title (may mirror metadata.title) |
| `created_at` | `string` (ISO-8601) | yes | Creation timestamp |
| `updated_at` | `string` (ISO-8601) | yes | Last DSL write timestamp |
| `source` | `object` | yes | Provenance of input content |
| `source.type` | `"pdf"\|"docx"\|"txt"\|"md"\|"topic"` | yes | Input kind |
| `source.ref` | `string` | yes | Path or topic key inside project store |
| `source.hash` | `string` | yes | Content hash for cache invalidation |
| `language` | `string` (BCP-47) | yes | Primary language, e.g. `en`, `hi` |
| `canvas` | `object` | yes | Default stage geometry |
| `canvas.width` | `integer` | yes | Pixel width (e.g. 1280) |
| `canvas.height` | `integer` | yes | Pixel height (e.g. 720) |
| `canvas.aspect_ratio` | `string` | yes | e.g. `"16:9"` |
| `canvas.fps` | `number` | yes | Frames per second target (e.g. 30) |
| `compile` | `object` | yes | Compiler metadata |
| `compile.graph_version` | `string` | yes | Orchestrator graph version |
| `compile.agent_versions` | `object` | yes | Map of agent_name → version string |
| `compile.engine_versions` | `object` | yes | Map of engine_name → version string |
| `status` | `"draft"\|"compiled"\|"timeline_bound"\|"render_ready"` | yes | DSL maturity stage |
| `notes` | `string` | no | Freeform engineering notes (not shown in video) |

### 4.2 Example

```json
{
  "id": "3f2a9c1e-5b44-4d2a-9c1e-112233445566",
  "title": "Binary Search Explained",
  "created_at": "2026-07-11T09:30:00Z",
  "updated_at": "2026-07-11T09:41:12Z",
  "source": {
    "type": "md",
    "ref": "source/input.md",
    "hash": "sha256:ab..."
  },
  "language": "en",
  "canvas": {
    "width": 1280,
    "height": 720,
    "aspect_ratio": "16:9",
    "fps": 30
  },
  "compile": {
    "graph_version": "1.0.0",
    "agent_versions": {
      "visual_planning_agent": "1.0.0",
      "layout_planner_agent": "1.0.0"
    },
    "engine_versions": {
      "presentation_engine": "1.0.0"
    }
  },
  "status": "compiled"
}
```

### 4.3 Validation Highlights

- `canvas.width` and `canvas.height` must match `aspect_ratio` within 1px tolerance  
- `status` may only advance (draft → compiled → timeline_bound → render_ready) unless a deliberate invalidation rewrite occurs  
- `source.hash` must be non-empty  

---

## 5. Metadata

Project-level descriptive data for library UI and export packages.

### 5.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `string` | yes | Display title |
| `description` | `string` | yes | Short summary (1–3 sentences) |
| `tags` | `string[]` | yes | Search tags (may be empty array) |
| `domain` | `string` | yes | Primary domain label |
| `subtopics` | `string[]` | no | Secondary labels |
| `difficulty` | `"beginner"\|"intermediate"\|"advanced"` | yes | Audience level |
| `estimated_duration_sec` | `number` | yes | Pre-timeline estimate |
| `actual_duration_sec` | `number` | no | Filled after timeline bind |
| `authors` | `string[]` | no | Optional attribution |
| `license` | `string` | no | Output license note |
| `thumbnail` | `object` | no | Thumbnail directive |
| `thumbnail.scene_id` | `string` | no | Preferred scene for capture |
| `thumbnail.object_id` | `string` | no | Optional focus object |
| `thumbnail.path` | `string` | no | Filled by renderer/output manager |
| `locale` | `object` | no | Localization bundle refs |
| `locale.source_lang` | `string` | no | Original language |
| `locale.target_lang` | `string` | no | If translated |
| `educational` | `object` | no | Pedagogy metadata |
| `educational.learning_objectives` | `string[]` | no | Objectives covered |
| `educational.prerequisites` | `string[]` | no | Assumed knowledge |

### 5.2 Example

```json
{
  "title": "Binary Search Explained",
  "description": "A visual walkthrough of binary search on a sorted array.",
  "tags": ["algorithms", "search", "computer-science"],
  "domain": "computer_science",
  "subtopics": ["algorithms", "divide_and_conquer"],
  "difficulty": "intermediate",
  "estimated_duration_sec": 180,
  "educational": {
    "learning_objectives": [
      "Define binary search preconditions",
      "Trace low, mid, and high pointers"
    ],
    "prerequisites": ["arrays", "sorted_order"]
  }
}
```

---

## 6. Theme

Themes skin the presentation without changing pedagogy.

### 6.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Theme pack ID (`notebooklm`, `whiteboard`, …) |
| `version` | `string` | yes | Theme pack version |
| `tokens` | `object` | yes | Resolved design tokens |
| `tokens.colors` | `object` | yes | Color map |
| `tokens.colors.bg` | `Color` | yes | Stage background default |
| `tokens.colors.fg` | `Color` | yes | Primary foreground |
| `tokens.colors.accent` | `Color` | yes | Accent |
| `tokens.colors.muted` | `Color` | yes | Secondary text/strokes |
| `tokens.colors.success` | `Color` | no | Positive highlight |
| `tokens.colors.warning` | `Color` | no | Caution highlight |
| `tokens.colors.danger` | `Color` | no | Error/mismatch highlight |
| `tokens.fonts` | `object` | yes | Font tokens |
| `tokens.fonts.display` | `string` | yes | Title font family key |
| `tokens.fonts.body` | `string` | yes | Body font family key |
| `tokens.fonts.mono` | `string` | no | Code font key |
| `tokens.stroke` | `object` | yes | Default stroke style |
| `tokens.stroke.weight` | `number` | yes | Default stroke width |
| `tokens.stroke.corner_radius` | `number` | yes | Default corner radius |
| `tokens.motion` | `object` | no | Default motion preferences |
| `tokens.motion.default_easing` | `EasingId` | no | Default easing |
| `tokens.motion.emphasis_scale` | `number` | no | Pulse scale factor |
| `icon_preference` | `string[]` | no | Ordered asset pack preference |
| `background_ Motif` | — | — | **Use `background` on scenes; theme may supply defaults via `defaults.background`** |
| `defaults` | `object` | no | Theme-provided defaults |
| `defaults.background` | `Background` | no | Default scene background |
| `overrides` | `object` | no | Per-project token overrides (validated) |

> Field name note: use `defaults.background`, not a misspelled root field.

### 6.2 Color Type

`Color` is one of:

- `#RRGGBB` or `#RRGGBBAA`  
- `{ "ref": "tokens.colors.accent" }` token reference (resolved at compile)

### 6.3 Example

```json
{
  "id": "notebooklm",
  "version": "1.0.0",
  "tokens": {
    "colors": {
      "bg": "#F7F4EF",
      "fg": "#1C1917",
      "accent": "#0F766E",
      "muted": "#78716C",
      "success": "#15803D",
      "warning": "#C2410C",
      "danger": "#B91C1C"
    },
    "fonts": {
      "display": "theme.notebooklm.display",
      "body": "theme.notebooklm.body",
      "mono": "theme.notebooklm.mono"
    },
    "stroke": { "weight": 2, "corner_radius": 10 },
    "motion": { "default_easing": "ease_in_out", "emphasis_scale": 1.04 }
  },
  "icon_preference": ["lucide", "heroicons", "openmoji"]
}
```

### 6.4 Validation

- Required color keys present  
- Font keys resolvable against installed font assets  
- Overrides cannot introduce unknown token paths in v1.0 core  

---

## 7. Assets

The `assets` array is the manifest of concrete files and procedural generators referenced by objects.

### 7.1 Asset Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Asset ID referenced by objects |
| `type` | `"svg"\|"png"\|"jpg"\|"webp"\|"font"\|"audio"\|"procedural"\|"icon_ref"` | yes | Asset kind |
| `source` | `string` | yes | Pack or generator name (`lucide`, `openmoji`, `procedural.array`, `project`) |
| `key` | `string` | no | Pack key (e.g. icon name) |
| `path` | `string` | no | Resolved filesystem path (required once resolved, except pure procedural) |
| `hash` | `string` | no | Content hash when file-backed |
| `meta` | `object` | no | Extra info (viewBox, size, license) |
| `meta.license` | `string` | no | License identifier |
| `meta.viewBox` | `string` | no | SVG viewBox |
| `meta.width` | `number` | no | Intrinsic width |
| `meta.height` | `number` | no | Intrinsic height |
| `generator` | `object` | no | For `type=procedural` |
| `generator.name` | `string` | yes* | Generator ID |
| `generator.params` | `object` | yes* | Generator parameters |
| `plugin` | `string` | no | Plugin ID if asset comes from plugin |

\* required when `type` is `procedural`

### 7.2 Example

```json
{
  "id": "icon_sun",
  "type": "icon_ref",
  "source": "openmoji",
  "key": "sun",
  "path": "assets/openmoji/sun.svg",
  "hash": "sha256:...",
  "meta": { "license": "CC-BY-SA-4.0", "viewBox": "0 0 72 72" }
}
```

```json
{
  "id": "array_main",
  "type": "procedural",
  "source": "procedural.array",
  "generator": {
    "name": "array_cells",
    "params": { "values": [2, 5, 8, 12, 16, 23, 38], "cell_w": 64, "cell_h": 64 }
  }
}
```

---

## 8. Voice

Narration configuration and bindings to audio artifacts.

### 8.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | `boolean` | yes | Whether narration audio is used |
| `provider` | `"piper"\|"plugin"` | yes | TTS backend |
| `voice_id` | `string` | yes | Local voice identifier |
| `language` | `string` | yes | BCP-47 |
| `sample_rate` | `integer` | no | Hz (e.g. 22050) |
| `speaking_rate` | `number` | no | 0.5–2.0 multiplier |
| `master_track` | `object` | no | Concatenated narration |
| `master_track.path` | `string` | no | Path to full narration file |
| `master_track.duration_sec` | `number` | no | Measured duration |
| `master_track.hash` | `string` | no | File hash |
| `beats` | `VoiceBeat[]` | yes | Per-narration units |

### 8.2 VoiceBeat Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Beat ID (`nar_01`) |
| `text` | `string` | yes | Spoken text |
| `scene_id` | `string` | yes | Target scene |
| `path` | `string` | no | Per-beat audio path |
| `duration_sec` | `number` | no | Measured duration |
| `start_sec` | `number` | no | Absolute start after timeline bind |
| `end_sec` | `number` | no | Absolute end after timeline bind |
| `viseme_ref` | `string` | no | Future lip-sync plugin hook |

### 8.3 Example

```json
{
  "enabled": true,
  "provider": "piper",
  "voice_id": "en_US-lessac-medium",
  "language": "en",
  "sample_rate": 22050,
  "speaking_rate": 1.0,
  "beats": [
    {
      "id": "nar_01",
      "text": "Binary search finds a target in a sorted array by repeatedly cutting the search space in half.",
      "scene_id": "scene_intro",
      "duration_sec": 7.8
    }
  ]
}
```

---

## 9. Subtitles

Timed text derived from voice beats (and optional alignment).

### 9.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | `boolean` | yes | Whether subtitles are produced |
| `language` | `string` | yes | BCP-47 |
| `burn_in` | `boolean` | yes | If true, renderer composites onto frames |
| `formats` | `("srt"\|"vtt")[]` | yes | Sidecar formats to emit |
| `paths` | `object` | no | Output paths after subtitle agent |
| `paths.srt` | `string` | no | SRT path |
| `paths.vtt` | `string` | no | VTT path |
| `cues` | `SubtitleCue[]` | yes | Cue list (may be empty before timing) |
| `style` | `object` | no | Burn-in style hints |
| `style.font_token` | `string` | no | Font token |
| `style.position` | `"bottom"\|"top"` | no | Safe-area position |
| `style.max_chars_per_line` | `integer` | no | Wrapping guidance |
| `style.max_lines` | `integer` | no | Usually 2 |

### 9.2 SubtitleCue Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Cue ID |
| `beat_id` | `string` | no | Source voice beat |
| `start_sec` | `number` | yes | Start time |
| `end_sec` | `number` | yes | End time (`>` start) |
| `text` | `string` | yes | Visible text |
| `scene_id` | `string` | no | Owning scene |

### 9.3 Example

```json
{
  "enabled": true,
  "language": "en",
  "burn_in": false,
  "formats": ["srt", "vtt"],
  "cues": [
    {
      "id": "cue_001",
      "beat_id": "nar_01",
      "start_sec": 0.0,
      "end_sec": 3.2,
      "text": "Binary search finds a target in a sorted array",
      "scene_id": "scene_intro"
    }
  ]
}
```

---

## 10. Layout System

Layouts define spatial regions. Defaults live at root; scenes may override.

### 10.1 `layout_defaults` Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `preset` | `string` | yes | e.g. `title_stage_caption` |
| `safe_margins` | `object` | yes | Normalized margins 0–1 |
| `safe_margins.top` | `number` | yes | |
| `safe_margins.right` | `number` | yes | |
| `safe_margins.bottom` | `number` | yes | |
| `safe_margins.left` | `number` | yes | |
| `regions` | `Region[]` | yes | Named regions |

### 10.2 Region Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Region name (`title`, `stage`, `caption`) |
| `x` | `number` | yes | Left, normalized 0–1 |
| `y` | `number` | yes | Top, normalized 0–1 |
| `w` | `number` | yes | Width, normalized |
| `h` | `number` | yes | Height, normalized |
| `z_base` | `integer` | no | Base z-index for region |

### 10.3 Scene `layout` Fields

Same as defaults, plus:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inherits_defaults` | `boolean` | no | Default `true` |
| `preset` | `string` | no | Override preset |
| `regions` | `Region[]` | no | Override/replace regions |

### 10.4 Example

```json
{
  "preset": "title_stage_caption",
  "safe_margins": { "top": 0.06, "right": 0.06, "bottom": 0.08, "left": 0.06 },
  "regions": [
    { "id": "title", "x": 0.06, "y": 0.06, "w": 0.88, "h": 0.12 },
    { "id": "stage", "x": 0.06, "y": 0.20, "w": 0.88, "h": 0.58 },
    { "id": "caption", "x": 0.06, "y": 0.80, "w": 0.88, "h": 0.10 }
  ]
}
```

---

## 11. Scene

A scene is one pedagogical unit on the timeline.

### 11.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Scene ID |
| `order` | `integer` | yes | 0-based ascending order |
| `purpose` | `string` | yes | Learning purpose statement |
| `visual_mode` | `VisualMode` | yes | See catalog below |
| `narration_beat_ids` | `string[]` | yes | Voice beats for this scene |
| `concept_ids` | `string[]` | no | Upstream knowledge concept refs |
| `background` | `Background` | yes | Scene background |
| `layout` | `Layout` | no | Scene layout override |
| `objects` | `SceneObject[]` | yes | Visual objects |
| `animations` | `Animation[]` | yes | Motion clips (may be empty pre-animation agent) |
| `camera` | `Camera` | yes | Camera plan for scene |
| `duration` | `Duration` | yes | Duration model for scene |
| `transitions` | `object` | no | In/out transitions |
| `transitions.in` | `Transition` | no | Enter transition |
| `transitions.out` | `Transition` | no | Exit transition |
| `notes` | `string` | no | Authoring notes |

### 11.2 VisualMode Enum (v1.0)

| Value | Use |
|-------|-----|
| `algorithm_trace` | Stepwise CS algorithms |
| `process_flow` | Biological/chemical processes |
| `system_diagram` | Networks / client-server |
| `compare_contrast` | Dual panels |
| `definition_card` | Short definitions |
| `chart_explain` | Quantitative charts |
| `equation_walkthrough` | Math reveal |
| `timeline_events` | Historical/process timelines |
| `code_walkthrough` | Programming code focus |
| `solar_map` | Orbital / spatial system maps |
| `custom` | Requires `extensions` explanation |

### 11.3 Transition Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"cut"\|"fade"\|"slide_left"\|"slide_right"\|"none"` | yes | Transition type |
| `duration_sec` | `number` | yes | ≥ 0 |

---

## 12. Background

### 12.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"solid"\|"gradient"\|"pattern"\|"image"\|"theme_default"` | yes | Background mode |
| `color` | `Color` | no | For `solid` |
| `gradient` | `object` | no | For `gradient` |
| `gradient.from` | `Color` | yes* | |
| `gradient.to` | `Color` | yes* | |
| `gradient.angle_deg` | `number` | no | Default 160 |
| `pattern` | `object` | no | For `pattern` |
| `pattern.id` | `string` | yes* | e.g. `dots`, `grid`, `paper` |
| `pattern.opacity` | `number` | no | 0–1 |
| `image` | `object` | no | For `image` (plugin/core asset) |
| `image.asset_id` | `string` | yes* | Asset ref |
| `image.fit` | `"cover"\|"contain"` | no | Default `cover` |
| `image.opacity` | `number` | no | 0–1 |

\* required for the corresponding `type`

### 12.2 Example

```json
{
  "type": "pattern",
  "pattern": { "id": "paper", "opacity": 0.35 },
  "color": "#F7F4EF"
}
```

---

## 13. Objects (Scene Elements)

Objects are the nouns of the presentation language.

### 13.1 Common Fields (All Kinds)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Scene-local object ID |
| `kind` | `string` | yes | Object kind from catalog |
| `name` | `string` | no | Debug-friendly name |
| `region` | `string` | no | Layout region id (`stage`, `title`, …) |
| `transform` | `Transform` | yes | Placement |
| `z_index` | `integer` | yes | Stacking order |
| `visible` | `boolean` | yes | Initial visibility |
| `opacity` | `number` | yes | 0–1 initial opacity |
| `style_tokens` | `string[]` | no | Semantic style tags |
| `theme_overrides` | `object` | no | Sparse concrete overrides (discouraged) |
| `props` | `object` | yes | Kind-specific properties |
| `accessibility` | `object` | no | Alt text / aria-like hints |
| `accessibility.label` | `string` | no | Short label |
| `accessibility.description` | `string` | no | Longer description |
| `locks` | `object` | no | Authoring locks for future editors |
| `plugin` | `string` | no | Plugin owning custom kind |
| `children` | `string[]` | no | Child object IDs for groups |

### 13.2 Transform Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | `number` | yes | Normalized center or top-left per `anchor` |
| `y` | `number` | yes | Normalized |
| `w` | `number` | yes | Normalized width |
| `h` | `number` | yes | Normalized height |
| `rotation_deg` | `number` | no | Default 0 |
| `anchor` | `"center"\|"top_left"` | no | Default `center` |
| `scale` | `number` | no | Uniform scale, default 1 |

**Coordinate system:** `(0,0)` is top-left of canvas; `(1,1)` is bottom-right. Object coordinates are relative to canvas unless `region` implies region-local packing (implementation may resolve region-local → canvas at compile).

**Normative v1.0 rule:** After Presentation Engine compile, all transforms in the DSL MUST be **canvas-normalized**. Region fields remain as authoring hints.

---

## 14. Object Kind Catalog

Each kind defines required `props`. Unknown core kinds are invalid unless declared under `extensions.object_kinds` by an enabled plugin.

### 14.1 `text`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `content` | `string` | yes | Display text |
| `role` | `"title"\|"subtitle"\|"body"\|"label"\|"caption"\|"code"` | yes | Typography role |
| `align` | `"left"\|"center"\|"right"` | no | Default `left` |
| `max_lines` | `integer` | no | Ellipsis policy |
| `markdown_inline` | `boolean` | no | Allow bold/italic only if true |

### 14.2 `shape`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `shape` | `"rect"\|"ellipse"\|"line"\|"polyline"\|"polygon"` | yes | Geometry |
| `points` | `number[][]` | no | For poly types, normalized points |
| `filled` | `boolean` | no | Default true |
| `stroke` | `boolean` | no | Default true |

### 14.3 `icon`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `asset_id` | `string` | yes | Asset ref |
| `tint_token` | `string` | no | Optional color token |

### 14.4 `image`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `asset_id` | `string` | yes | Raster/SVG asset |
| `fit` | `"contain"\|"cover"` | no | Default `contain` |
| `rounded` | `number` | no | Corner radius px or normalized policy |

> Core v1.0 may use `image` for Undraw/SVG illustrations. Generative images require plugin metadata.

### 14.5 `arrow`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `from` | `object` | yes | `{ "x", "y" }` or `{ "object_id", "anchor?" }` |
| `to` | `object` | yes | Same as `from` |
| `head` | `"none"\|"end"\|"both"` | no | Default `end` |
| `curvature` | `number` | no | 0 = straight |
| `label` | `string` | no | Mid-arrow label |

### 14.6 `label_callout`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `text` | `string` | yes | Callout text |
| `target_object_id` | `string` | no | Object being labeled |
| `placement` | `"n"\|"e"\|"s"\|"w"\|"ne"\|"nw"\|"se"\|"sw"` | no | Relative placement |

### 14.7 `array`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `values` | `(number\|string\|null)[]` | yes | Cell values |
| `sorted` | `boolean` | no | Visual hint |
| `highlight_indices` | `integer[]` | no | Highlighted cells |
| `disabled_indices` | `integer[]` | no | Greyed-out cells |
| `cell_label_mode` | `"value"\|"index"\|"both"` | no | Default `value` |
| `orientation` | `"horizontal"\|"vertical"` | no | Default `horizontal` |

### 14.8 `pointer`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `label` | `string` | yes | e.g. `low`, `mid`, `high` |
| `target` | `string` | yes | Address like `arr[3]` or object cell ref |
| `direction` | `"up"\|"down"\|"left"\|"right"` | no | Default `down` |

### 14.9 `graph` / `tree`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `nodes` | `object[]` | yes | `{ id, label, group? }` |
| `edges` | `object[]` | yes | `{ from, to, label? }` |
| `layout` | `"auto"\|"layered"\|"radial"` | no | Default `auto` |
| `active_node_ids` | `string[]` | no | Emphasis |
| `active_edge_ids` | `string[]` | no | Emphasis |

### 14.10 `packet` / `token`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `label` | `string` | no | Packet name |
| `path_object_id` | `string` | no | Edge/path to follow |
| `payload` | `string` | no | Small payload tag |

### 14.11 `chart`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `chart_type` | `"bar"\|"line"\|"pie"` | yes | |
| `series` | `object[]` | yes | Data series |
| `x_labels` | `string[]` | no | Categories |
| `show_legend` | `boolean` | no | Default true |
| `highlight_index` | `integer` | no | Emphasize category |

### 14.12 `equation`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `latex` | `string` | no | If engine supports |
| `parts` | `string[]` | yes | Revealable parts (plain or latex fragments) |
| `visible_part_count` | `integer` | no | How many parts shown initially |

### 14.13 `code_block`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `language` | `string` | yes | e.g. `python` |
| `lines` | `string[]` | yes | Code lines |
| `highlight_lines` | `integer[]` | no | 1-based lines |
| `focus_line` | `integer` | no | Camera/anim focus |

### 14.14 `process_step`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `index` | `integer` | yes | Step number |
| `title` | `string` | yes | Step title |
| `icon_asset_id` | `string` | no | Optional icon |
| `state` | `"pending"\|"active"\|"done"` | yes | Visual state |

### 14.15 `planet` / `orbit` (solar / spatial)

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `label` | `string` | yes | Name |
| `orbit_radius` | `number` | yes | Normalized radius from center object |
| `angle_deg` | `number` | yes | Current angle |
| `parent_id` | `string` | yes | Center body object ID |
| `body_asset_id` | `string` | no | Icon/SVG for body |
| `show_orbit_path` | `boolean` | no | Default true |

### 14.16 `timeline_track`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `events` | `object[]` | yes | `{ id, label, t, description? }` where `t` is 0–1 along track |
| `orientation` | `"horizontal"\|"vertical"` | no | Default `horizontal` |
| `active_event_id` | `string` | no | Emphasis |

### 14.17 `group`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `layout` | `"free"\|"row"\|"column"\|"stack"` | no | Child layout hint |
| `gap` | `number` | no | Normalized gap |

Children listed in `children` IDs.

### 14.18 `comparison_panel`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `left_title` | `string` | yes | |
| `right_title` | `string` | yes | |
| `left_object_ids` | `string[]` | yes | |
| `right_object_ids` | `string[]` | yes | |

---

## 15. Animations

Animations are declarative motion intents attached to a scene. Absolute timing may be scene-relative until the Timeline compiler promotes them.

### 15.1 Animation Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Animation ID |
| `target_object_id` | `string` | yes | Object to animate |
| `preset` | `AnimationPreset` | yes | Motion preset name |
| `t` | `[number, number]` | yes | Scene-relative normalized start/end in `[0,1]` OR seconds if `time_unit` is `sec` |
| `time_unit` | `"normalized"\|"sec"` | yes | Interpretation of `t` |
| `easing` | `EasingId` | no | Default from theme |
| `params` | `object` | no | Preset-specific parameters |
| `narration_beat_id` | `string` | no | Optional sync anchor |
| `loop` | `boolean` | no | Default false |
| `priority` | `integer` | no | Conflict resolution hint |

### 15.2 Animation Presets (v1.0)

| Preset | Params (common) | Meaning |
|--------|-----------------|---------|
| `fade_in` | — | Opacity 0→1 |
| `fade_out` | — | Opacity 1→0 |
| `slide_in` | `from`: `left\|right\|top\|bottom` | Enter from edge |
| `slide_out` | `to`: direction | Exit |
| `scale_in` | `from_scale` | Pop in |
| `emphasize` | `scale?` | Pulse emphasis |
| `move_to` | `to`: transform or pointer target | Move |
| `highlight_set` | `indices` / `node_ids` | Change highlight props |
| `typewriter` | `cps?` | Reveal text |
| `draw_arrow` | — | Stroke draw |
| `follow_path` | `path_object_id` | Token/packet motion |
| `orbit` | `delta_angle_deg` | Planet motion |
| `reveal_parts` | `count` | Equation/code reveal |
| `state_set` | `prop`, `value` | Discrete prop change |
| `camera_focus_proxy` | — | Reserved; prefer Camera track |

### 15.3 EasingId

`linear` | `ease_in` | `ease_out` | `ease_in_out` | `ease_in_cubic` | `ease_out_cubic`

### 15.4 Example

```json
{
  "id": "anim_mid_move",
  "target_object_id": "ptr_mid",
  "preset": "move_to",
  "time_unit": "normalized",
  "t": [0.35, 0.55],
  "easing": "ease_in_out",
  "params": { "to": { "target": "arr[3]" } },
  "narration_beat_id": "nar_02"
}
```

---

## 16. Camera

Camera frames the stage. It does not create new pedagogical objects.

### 16.1 Camera Fields (per scene)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `preset` | `string` | yes | e.g. `full_stage`, `focus_object` |
| `initial` | `CameraTransform` | yes | Starting view |
| `keyframes` | `CameraKeyframe[]` | yes | Motion keyframes (may be empty) |
| `limits` | `object` | no | Safety clamps |
| `limits.max_zoom` | `number` | no | e.g. 2.5 |
| `limits.min_zoom` | `number` | no | e.g. 1.0 |
| `limits.max_pan_speed` | `number` | no | Normalized units/sec |

### 16.2 CameraTransform

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | `number` | yes | View center x (normalized) |
| `y` | `number` | yes | View center y |
| `zoom` | `number` | yes | 1 = full stage |
| `rotation_deg` | `number` | no | Default 0 (avoid unless necessary) |

### 16.3 CameraKeyframe

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | |
| `t` | `number` | yes | Scene-relative normalized or sec (see `time_unit`) |
| `time_unit` | `"normalized"\|"sec"` | yes | |
| `transform` | `CameraTransform` | yes | Target view |
| `easing` | `EasingId` | no | |
| `focus_object_id` | `string` | no | Helper for compilers |

### 16.4 Example

```json
{
  "preset": "focus_object",
  "initial": { "x": 0.5, "y": 0.5, "zoom": 1.0 },
  "keyframes": [
    {
      "id": "cam_01",
      "t": 0.2,
      "time_unit": "normalized",
      "transform": { "x": 0.5, "y": 0.48, "zoom": 1.25 },
      "focus_object_id": "arr",
      "easing": "ease_in_out"
    }
  ],
  "limits": { "max_zoom": 2.0, "min_zoom": 1.0 }
}
```

---

## 17. Timeline

The root `timeline` is the absolute-time compilation consumed by the renderer. Scene-local animation `t` values are inputs; timeline tracks are outputs of the Animation Engine.

### 17.1 Timeline Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | `string` | yes | Timeline schema version (`1.0`) |
| `fps` | `number` | yes | Must match `project.canvas.fps` |
| `duration_sec` | `number` | yes | Total media duration |
| `status` | `"unbound"\|"bound"\|"locked"` | yes | Bind state |
| `tracks` | `TimelineTrack[]` | yes | Parallel tracks |
| `markers` | `TimelineMarker[]` | yes | Scene boundaries etc. |
| `bindings` | `object` | no | Traceability |
| `bindings.voice_master` | `string` | no | Voice master path |
| `bindings.dsl_hash` | `string` | no | Hash of DSL scenes used to compile |

### 17.2 TimelineTrack Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Track ID |
| `type` | `"scene"\|"animation"\|"camera"\|"audio"\|"subtitle"\|"transition"` | yes | Track kind |
| `clips` | `TimelineClip[]` | yes | Timed clips |

### 17.3 TimelineClip Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | Clip ID |
| `ref_type` | `string` | yes | e.g. `scene`, `animation`, `voice_beat` |
| `ref_id` | `string` | yes | Referenced entity ID |
| `start_sec` | `number` | yes | Absolute start |
| `end_sec` | `number` | yes | Absolute end |
| `payload` | `object` | no | Compiled keyframes / encoder hints |

### 17.4 TimelineMarker Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | yes | |
| `t_sec` | `number` | yes | Absolute time |
| `label` | `string` | yes | e.g. scene title |
| `scene_id` | `string` | no | |

### 17.5 Example (abbreviated)

```json
{
  "version": "1.0",
  "fps": 30,
  "duration_sec": 42.5,
  "status": "bound",
  "markers": [
    { "id": "m1", "t_sec": 0.0, "label": "Intro", "scene_id": "scene_intro" },
    { "id": "m2", "t_sec": 8.0, "label": "Trace", "scene_id": "scene_trace" }
  ],
  "tracks": [
    {
      "id": "trk_scenes",
      "type": "scene",
      "clips": [
        { "id": "c1", "ref_type": "scene", "ref_id": "scene_intro", "start_sec": 0.0, "end_sec": 8.0 }
      ]
    },
    {
      "id": "trk_audio",
      "type": "audio",
      "clips": [
        { "id": "a1", "ref_type": "voice_beat", "ref_id": "nar_01", "start_sec": 0.0, "end_sec": 7.8 }
      ]
    }
  ]
}
```

---

## 18. Duration Model

Duration appears at scene level and rolls up to timeline totals.

### 18.1 Scene `duration` Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | `"from_narration"\|"fixed"\|"max_of"\|"manual"` | yes | How duration is chosen |
| `hint_sec` | `number` | no | Planner hint before audio exists |
| `fixed_sec` | `number` | no | When mode is `fixed` |
| `min_sec` | `number` | no | Clamp |
| `max_sec` | `number` | no | Clamp |
| `resolved_sec` | `number` | no | Filled after bind |
| `pad_before_sec` | `number` | no | Silence/hold before narration |
| `pad_after_sec` | `number` | no | Hold after narration |

### 18.2 Resolution Rules

1. If `mode=from_narration`: sum of bound beats (+ pads)  
2. If `mode=fixed`: use `fixed_sec` (beats must fit or be rejected)  
3. If `mode=max_of`: max(narration, animation span, hint) within clamps  
4. `resolved_sec` required before `project.status=render_ready`  

### 18.3 Project Duration

`metadata.actual_duration_sec` MUST equal `timeline.duration_sec` when status is `render_ready`.

---

## 19. Coordinate, Color & Style Systems

### 19.1 Coordinates

- Normalized canvas space `[0,1]`  
- Positive Y downward  
- z_index integer; higher draws above  

### 19.2 Style Tokens (Semantic)

Examples:

| Token | Meaning |
|-------|---------|
| `emphasis-neutral` | Default teaching emphasis |
| `emphasis-positive` | Correct / match |
| `emphasis-negative` | Discard / mismatch |
| `muted` | De-emphasized |
| `title` | Title styling |
| `code` | Monospace treatment |

Theme maps tokens → concrete colors/fonts/strokes.

### 19.3 Why Semantic Tokens Matter

Changing `theme.id` from `notebooklm` to `dark` must not require rewriting object props. Only token resolution changes.

---

## 20. Validation Rules

Validation runs at compile boundaries. Violations are `error` (block) or `warning` (allow with log).

### 20.1 Global

| ID | Severity | Rule |
|----|----------|------|
| G001 | error | `dsl_version` must be supported by engine |
| G002 | error | JSON must parse; root must be object |
| G003 | error | `project.id` UUID format |
| G004 | error | Scene `order` unique contiguous from 0 |
| G005 | error | All referenced IDs resolve |
| G006 | error | No cycles in `group.children` |
| G007 | warning | Empty `scenes` |
| G008 | error | `timeline.fps` == `project.canvas.fps` when timeline bound |

### 20.2 Scenes & Objects

| ID | Severity | Rule |
|----|----------|------|
| S001 | error | `objects[].kind` known or plugin-registered |
| S002 | error | Kind-required props present and typed |
| S003 | error | Transforms within canvas bounds soft-check (center may be inside) |
| S004 | warning | More than 40 objects in one scene |
| S005 | error | Duplicate object IDs in a scene |
| S006 | warning | `visual_mode` incompatible with dominant kinds (heuristic) |

### 20.3 Animation & Camera

| ID | Severity | Rule |
|----|----------|------|
| A001 | error | `target_object_id` exists |
| A002 | error | `t[0] <= t[1]` |
| A003 | error | Normalized `t` within `[0,1]` |
| A004 | warning | Overlapping animations on same property without priority |
| C001 | error | Zoom within limits |
| C002 | warning | Camera rotation ≠ 0 |

### 20.4 Voice & Subtitles

| ID | Severity | Rule |
|----|----------|------|
| V001 | error | If `voice.enabled`, beats non-empty for narrated projects |
| V002 | error | Beat `scene_id` exists |
| U001 | error | Cue `end_sec > start_sec` |
| U002 | warning | Cue text > 84 chars |
| U003 | error | If burn-in, cues must be bound |

### 20.5 Timeline & Duration

| ID | Severity | Rule |
|----|----------|------|
| T001 | error | No overlapping scene clips on scene track |
| T002 | error | `duration_sec` ≥ last clip end |
| T003 | error | Audio clips reference existing beats |
| D001 | error | `render_ready` requires all `duration.resolved_sec` |

### 20.6 Theme & Assets

| ID | Severity | Rule |
|----|----------|------|
| H001 | error | Theme id installed or bundled |
| H002 | warning | Low contrast fg/bg estimate |
| P001 | error | File-backed assets have resolvable paths when status ≥ `compiled` |
| P002 | error | Procedural assets include generator name |

---

## 21. Versioning

### 21.1 `dsl_version`

Format: `"MAJOR.MINOR"` string.

| Change Type | Version Impact |
|-------------|----------------|
| Bugfix to docs only | Document version only |
| Additive optional fields | `MINOR` bump (1.0 → 1.1) |
| New object kinds in core | `MINOR` if optional; `MAJOR` if renderers must understand |
| Meaning change of existing field | `MAJOR` (2.0) |
| Removal of field | `MAJOR` |

### 21.2 Compatibility

Engines MUST:

1. Reject unsupported MAJOR  
2. Accept older MINOR within same MAJOR if compatible  
3. Ignore unknown optional fields only when `extensions.strict` is false **and** fields live under `extensions` (see §22)  

**Normative:** Unknown fields at **core** paths are errors in v1.0 strict mode (default).

### 21.3 Timeline Version

`timeline.version` is independent but should advance with breaking track payload changes.

### 21.4 File Naming

Recommended artifact names:

- `presentation.dsl.json`  
- `timeline.json` (may be embedded or sibling; if sibling, root DSL `timeline` may store ref)

**Embedding policy (v1.0):** Timeline MAY be embedded in the DSL document OR stored as a sibling file referenced by:

```json
"timeline": { "$ref": "artifacts/timeline.json", "version": "1.0", "status": "bound" }
```

If `$ref` is used, other timeline fields live in the referenced file.

---

## 22. Extensibility & Plugins

### 22.1 Extension Object

```json
{
  "extensions": {
    "strict": true,
    "plugins": ["plugin.watercolor_theme", "plugin.flux_images"],
    "object_kinds": {
      "watercolor_wash": {
        "plugin": "plugin.watercolor_theme",
        "schema_ref": "plugins/watercolor/kinds/wash.json"
      }
    },
    "animation_presets": {
      "ink_bleed": { "plugin": "plugin.watercolor_theme" }
    },
    "data": {
      "plugin.flux_images": { "seed": 42 }
    }
  }
}
```

### 22.2 Plugin Extension Rules

| Rule | Statement |
|------|-----------|
| E1 | Plugins register new `kind` values with `plugin` field on objects |
| E2 | Core renderer ignores unknown plugin kinds only if a fallback codec is provided; otherwise fail validation |
| E3 | Plugins MUST NOT redefine core kind semantics |
| E4 | Plugin fields live under `props` and/or `extensions.data[plugin_id]` |
| E5 | Enabling a plugin is a project config concern; DSL records which plugins were active at compile |
| E6 | Image generation plugins may add assets with `"type":"png"` and `"plugin":"..."` |

### 22.3 Forward Compatibility Pattern

Prefer:

```json
{
  "id": "hero_img",
  "kind": "image",
  "plugin": "plugin.flux_images",
  "props": {
    "asset_id": "gen_01",
    "fit": "contain"
  }
}
```

over inventing unversioned top-level keys.

### 22.4 Theme Plugins

New themes appear as theme packs; they do not need new DSL MAJOR if they only supply tokens.

### 22.5 When to Bump DSL vs Plugin

| Situation | Mechanism |
|-----------|-----------|
| New optional core kind used widely | DSL MINOR |
| Experimental visual | Plugin kind |
| Breaking camera model | DSL MAJOR |

---

## 23. How Agents Read and Write the DSL

Agents never share mutable objects. They read artifact snapshots and write new snapshots (or controlled enrichments through the Presentation Engine).

### 23.1 Agent × DSL Matrix

| Agent | Reads DSL? | Writes DSL? | What they write |
|-------|------------|-------------|-----------------|
| Parser / Cleaning / Structure / Knowledge / Topic / Difficulty / Strategy | No | No | Upstream JSON plans only |
| Script Agent | No | No | Narration script (voice texts later copied) |
| Scene Planner | No | No | ScenePlan (purposes, beat maps) |
| Metadata Agent | Partial | Yes (metadata section) | `metadata` |
| Visual Planning Agent | No | No | VisualPlan (modes, primitives, steps) |
| Layout Planner | Draft optional | Via engine | Layout regions → objects transforms |
| Theme Planner | Yes | Yes | `theme` |
| Asset Agent | Yes | Yes | `assets` + object `asset_id` links |
| **Presentation Engine** (called by planners) | Yes | Yes | Compiles full `scenes[].objects`, backgrounds, layouts |
| Animation Agent | Yes | Yes | `scenes[].animations` |
| Camera Agent | Yes | Yes | `scenes[].camera` |
| Translation Agent | Yes | Yes | Translated `voice.beats[].text`, subtitle texts, metadata strings |
| Voice Agent | Yes | Yes | `voice` paths/durations |
| Subtitle Agent | Yes | Yes | `subtitles` |
| Animation Engine | Yes | Yes | `timeline` bind |
| Rendering Agent | Yes | No (except output paths in metadata.thumbnail) | Consumes only |
| Project Manager | Yes | Yes (status/timestamps) | Lifecycle fields |

### 23.2 Write Protocols

1. **Compile write:** Presentation Engine produces `status=compiled` DSL from plans.  
2. **Enrichment write:** Animation/Camera/Voice/Subtitle agents add sections without changing unrelated pedagogy props.  
3. **Bind write:** Animation Engine sets `timeline` and `duration.resolved_sec`, status → `timeline_bound`.  
4. **Render-ready:** Output checks pass → `render_ready`.  

### 23.3 Forbidden Writes

- Voice Agent changing `array.values`  
- Renderer changing narration text  
- Theme Planner rewriting `purpose` or concept IDs  
- Any agent removing upstream IDs silently  

### 23.4 Enrichment Patch Model (Conceptual)

Although storage may rewrite a full JSON file, logically updates are patches:

```json
{
  "patch_id": "...",
  "author_agent": "animation_agent",
  "base_dsl_hash": "sha256:...",
  "ops": [
    { "op": "replace", "path": "/scenes/1/animations", "value": [ ... ] }
  ]
}
```

Implementations may apply patches or write full documents; validators always run on the result.

---

## 24. Renderer Contract

### 24.1 What the Renderer May Read

- `project.canvas`  
- `theme` (resolved)  
- `assets` (resolved paths)  
- `scenes` (objects, backgrounds)  
- `timeline` (absolute clips/keyframes)  
- `voice.master_track` / beat audio paths  
- `subtitles` (if burn-in)  

### 24.2 What the Renderer Must Never Do

```
NEVER call Ollama / LLM agents
NEVER invent missing objects
NEVER re-plan scenes
NEVER change pedagogical props
NEVER require network
```

If something required for pixels is missing, the renderer **fails** with a structured error (`RENDER_INPUT_INCOMPLETE`).

### 24.3 Why Isolation Matters

| Benefit | Explanation |
|---------|-------------|
| Determinism | Re-render same DSL → same frames policy |
| Testability | Golden DSL fixtures without AI |
| Reliability | Encode failures don’t need AI retries |
| Security | Render workers need no model credentials |
| Scalability | Cloud render plugin can accept DSL packages only |

### 24.4 Minimum Render-Ready Checklist

- [ ] `dsl_version` supported  
- [ ] All assets resolved  
- [ ] Timeline `status=bound` or `locked`  
- [ ] Voice durations present if voice enabled  
- [ ] No validation errors  
- [ ] `project.status=render_ready`  

---

## 25. Worked Examples

> Examples are illustrative and abbreviated. Real documents include full project/theme/voice sections.

---

### 25.1 Solar System

**Visual mode:** `solar_map`  
**Primitives:** sun body, orbit paths, planets, labels, gentle orbit animation  

```json
{
  "dsl_version": "1.0",
  "project": {
    "id": "11111111-1111-1111-1111-111111111111",
    "title": "Solar System Overview",
    "created_at": "2026-07-11T10:00:00Z",
    "updated_at": "2026-07-11T10:05:00Z",
    "source": { "type": "topic", "ref": "topic:solar-system", "hash": "sha256:ss1" },
    "language": "en",
    "canvas": { "width": 1280, "height": 720, "aspect_ratio": "16:9", "fps": 30 },
    "compile": {
      "graph_version": "1.0.0",
      "agent_versions": {},
      "engine_versions": { "presentation_engine": "1.0.0" }
    },
    "status": "compiled"
  },
  "metadata": {
    "title": "Solar System Overview",
    "description": "Planets orbiting the Sun with labels.",
    "tags": ["astronomy", "space"],
    "domain": "science",
    "difficulty": "beginner",
    "estimated_duration_sec": 90
  },
  "theme": {
    "id": "dark",
    "version": "1.0.0",
    "tokens": {
      "colors": {
        "bg": "#0B1020",
        "fg": "#F8FAFC",
        "accent": "#FBBF24",
        "muted": "#94A3B8"
      },
      "fonts": { "display": "theme.dark.display", "body": "theme.dark.body" },
      "stroke": { "weight": 2, "corner_radius": 8 }
    }
  },
  "assets": [
    { "id": "body_sun", "type": "icon_ref", "source": "openmoji", "key": "sun", "path": "assets/openmoji/sun.svg" },
    { "id": "body_earth", "type": "icon_ref", "source": "openmoji", "key": "earth-africa", "path": "assets/openmoji/earth.svg" }
  ],
  "voice": {
    "enabled": true,
    "provider": "piper",
    "voice_id": "en_US-lessac-medium",
    "language": "en",
    "beats": [
      {
        "id": "nar_sun",
        "text": "The Sun sits at the center of our solar system, and planets travel around it on orbits.",
        "scene_id": "scene_orbits",
        "duration_sec": 8.5
      }
    ]
  },
  "subtitles": {
    "enabled": true,
    "language": "en",
    "burn_in": false,
    "formats": ["srt", "vtt"],
    "cues": []
  },
  "layout_defaults": {
    "preset": "title_stage_caption",
    "safe_margins": { "top": 0.06, "right": 0.06, "bottom": 0.08, "left": 0.06 },
    "regions": [
      { "id": "title", "x": 0.06, "y": 0.05, "w": 0.88, "h": 0.1 },
      { "id": "stage", "x": 0.06, "y": 0.16, "w": 0.88, "h": 0.66 },
      { "id": "caption", "x": 0.06, "y": 0.84, "w": 0.88, "h": 0.08 }
    ]
  },
  "scenes": [
    {
      "id": "scene_orbits",
      "order": 0,
      "purpose": "Show Sun-centered orbits and name Earth",
      "visual_mode": "solar_map",
      "narration_beat_ids": ["nar_sun"],
      "background": { "type": "solid", "color": "#0B1020" },
      "objects": [
        {
          "id": "title",
          "kind": "text",
          "region": "title",
          "transform": { "x": 0.5, "y": 0.1, "w": 0.8, "h": 0.08, "anchor": "center" },
          "z_index": 10,
          "visible": true,
          "opacity": 1,
          "style_tokens": ["title"],
          "props": { "content": "The Solar System", "role": "title", "align": "center" }
        },
        {
          "id": "sun",
          "kind": "icon",
          "region": "stage",
          "transform": { "x": 0.5, "y": 0.5, "w": 0.12, "h": 0.12, "anchor": "center" },
          "z_index": 5,
          "visible": true,
          "opacity": 1,
          "props": { "asset_id": "body_sun" }
        },
        {
          "id": "earth",
          "kind": "planet",
          "region": "stage",
          "transform": { "x": 0.72, "y": 0.5, "w": 0.05, "h": 0.05, "anchor": "center" },
          "z_index": 6,
          "visible": true,
          "opacity": 1,
          "props": {
            "label": "Earth",
            "orbit_radius": 0.22,
            "angle_deg": 0,
            "parent_id": "sun",
            "body_asset_id": "body_earth",
            "show_orbit_path": true
          }
        },
        {
          "id": "earth_label",
          "kind": "label_callout",
          "transform": { "x": 0.80, "y": 0.42, "w": 0.12, "h": 0.05, "anchor": "center" },
          "z_index": 7,
          "visible": true,
          "opacity": 1,
          "props": { "text": "Earth", "target_object_id": "earth", "placement": "ne" }
        }
      ],
      "animations": [
        {
          "id": "anim_orbit",
          "target_object_id": "earth",
          "preset": "orbit",
          "time_unit": "normalized",
          "t": [0.1, 0.95],
          "easing": "linear",
          "params": { "delta_angle_deg": 50 }
        }
      ],
      "camera": {
        "preset": "full_stage",
        "initial": { "x": 0.5, "y": 0.5, "zoom": 1.0 },
        "keyframes": []
      },
      "duration": { "mode": "from_narration", "hint_sec": 9, "pad_after_sec": 0.4 }
    }
  ],
  "timeline": { "version": "1.0", "fps": 30, "duration_sec": 0, "status": "unbound", "tracks": [], "markers": [] },
  "extensions": { "strict": true, "plugins": [] }
}
```

---

### 25.2 Binary Search

**Visual mode:** `algorithm_trace`

```json
{
  "dsl_version": "1.0",
  "scenes": [
    {
      "id": "scene_trace",
      "order": 1,
      "purpose": "Trace one comparison step with low, mid, and high",
      "visual_mode": "algorithm_trace",
      "narration_beat_ids": ["nar_compare"],
      "background": { "type": "theme_default" },
      "objects": [
        {
          "id": "title",
          "kind": "text",
          "transform": { "x": 0.5, "y": 0.1, "w": 0.8, "h": 0.08, "anchor": "center" },
          "z_index": 1,
          "visible": true,
          "opacity": 1,
          "props": { "content": "Binary Search", "role": "title", "align": "center" }
        },
        {
          "id": "arr",
          "kind": "array",
          "transform": { "x": 0.5, "y": 0.48, "w": 0.78, "h": 0.16, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "style_tokens": ["emphasis-neutral"],
          "props": {
            "values": [2, 5, 8, 12, 16, 23, 38],
            "sorted": true,
            "highlight_indices": [3],
            "disabled_indices": [],
            "cell_label_mode": "value",
            "orientation": "horizontal"
          }
        },
        {
          "id": "ptr_low",
          "kind": "pointer",
          "transform": { "x": 0.18, "y": 0.66, "w": 0.08, "h": 0.08, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": { "label": "low", "target": "arr[0]", "direction": "up" }
        },
        {
          "id": "ptr_mid",
          "kind": "pointer",
          "transform": { "x": 0.5, "y": 0.66, "w": 0.08, "h": 0.08, "anchor": "center" },
          "z_index": 4,
          "visible": true,
          "opacity": 1,
          "style_tokens": ["emphasis-positive"],
          "props": { "label": "mid", "target": "arr[3]", "direction": "up" }
        },
        {
          "id": "ptr_high",
          "kind": "pointer",
          "transform": { "x": 0.82, "y": 0.66, "w": 0.08, "h": 0.08, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": { "label": "high", "target": "arr[6]", "direction": "up" }
        },
        {
          "id": "cmp_arrow",
          "kind": "arrow",
          "transform": { "x": 0.5, "y": 0.36, "w": 0.2, "h": 0.08, "anchor": "center" },
          "z_index": 5,
          "visible": true,
          "opacity": 1,
          "props": {
            "from": { "object_id": "ptr_mid" },
            "to": { "object_id": "arr" },
            "head": "end",
            "label": "compare"
          }
        }
      ],
      "animations": [
        {
          "id": "hl_mid",
          "target_object_id": "arr",
          "preset": "highlight_set",
          "time_unit": "normalized",
          "t": [0.2, 0.35],
          "params": { "indices": [3] }
        },
        {
          "id": "narrow",
          "target_object_id": "arr",
          "preset": "state_set",
          "time_unit": "normalized",
          "t": [0.6, 0.75],
          "params": { "prop": "disabled_indices", "value": [0, 1, 2] }
        }
      ],
      "camera": {
        "preset": "focus_object",
        "initial": { "x": 0.5, "y": 0.5, "zoom": 1.0 },
        "keyframes": [
          {
            "id": "cam_arr",
            "t": 0.15,
            "time_unit": "normalized",
            "transform": { "x": 0.5, "y": 0.5, "zoom": 1.2 },
            "focus_object_id": "arr",
            "easing": "ease_in_out"
          }
        ]
      },
      "duration": { "mode": "from_narration", "hint_sec": 12 }
    }
  ]
}
```

---

### 25.3 Photosynthesis

**Visual mode:** `process_flow`

```json
{
  "scenes": [
    {
      "id": "scene_photo",
      "order": 0,
      "purpose": "Show inputs Sun, water, CO₂ producing glucose and O₂",
      "visual_mode": "process_flow",
      "narration_beat_ids": ["nar_photo"],
      "background": {
        "type": "gradient",
        "gradient": { "from": "#ECFDF5", "to": "#FFFBEB", "angle_deg": 160 }
      },
      "objects": [
        {
          "id": "sun",
          "kind": "icon",
          "transform": { "x": 0.18, "y": 0.28, "w": 0.1, "h": 0.1, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "asset_id": "icon_sun" }
        },
        {
          "id": "leaf",
          "kind": "icon",
          "transform": { "x": 0.5, "y": 0.5, "w": 0.16, "h": 0.16, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "asset_id": "icon_leaf" }
        },
        {
          "id": "h2o",
          "kind": "text",
          "transform": { "x": 0.2, "y": 0.62, "w": 0.12, "h": 0.06, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "content": "H₂O", "role": "label", "align": "center" }
        },
        {
          "id": "co2",
          "kind": "text",
          "transform": { "x": 0.2, "y": 0.72, "w": 0.12, "h": 0.06, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "content": "CO₂", "role": "label", "align": "center" }
        },
        {
          "id": "arrow_in",
          "kind": "arrow",
          "transform": { "x": 0.34, "y": 0.55, "w": 0.12, "h": 0.05, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": { "from": { "object_id": "sun" }, "to": { "object_id": "leaf" }, "head": "end", "label": "energy" }
        },
        {
          "id": "glucose",
          "kind": "process_step",
          "transform": { "x": 0.78, "y": 0.42, "w": 0.18, "h": 0.1, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "index": 1, "title": "Glucose", "state": "pending" }
        },
        {
          "id": "o2",
          "kind": "process_step",
          "transform": { "x": 0.78, "y": 0.58, "w": 0.18, "h": 0.1, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "index": 2, "title": "O₂", "state": "pending" }
        },
        {
          "id": "arrow_out",
          "kind": "arrow",
          "transform": { "x": 0.64, "y": 0.5, "w": 0.1, "h": 0.05, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": { "from": { "object_id": "leaf" }, "to": { "object_id": "glucose" }, "head": "end" }
        }
      ],
      "animations": [
        {
          "id": "draw_in",
          "target_object_id": "arrow_in",
          "preset": "draw_arrow",
          "time_unit": "normalized",
          "t": [0.15, 0.35]
        },
        {
          "id": "activate_out",
          "target_object_id": "glucose",
          "preset": "state_set",
          "time_unit": "normalized",
          "t": [0.55, 0.65],
          "params": { "prop": "state", "value": "active" }
        }
      ],
      "camera": {
        "preset": "full_stage",
        "initial": { "x": 0.5, "y": 0.5, "zoom": 1.0 },
        "keyframes": []
      },
      "duration": { "mode": "from_narration", "hint_sec": 14 }
    }
  ]
}
```

---

### 25.4 Networking

**Visual mode:** `system_diagram`

```json
{
  "scenes": [
    {
      "id": "scene_req_res",
      "order": 0,
      "purpose": "Animate a request packet from client to server and a response back",
      "visual_mode": "system_diagram",
      "narration_beat_ids": ["nar_net"],
      "background": { "type": "solid", "color": "#F8FAFC" },
      "objects": [
        {
          "id": "client",
          "kind": "shape",
          "transform": { "x": 0.22, "y": 0.5, "w": 0.18, "h": 0.16, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "shape": "rect", "filled": true, "stroke": true }
        },
        {
          "id": "client_label",
          "kind": "text",
          "transform": { "x": 0.22, "y": 0.5, "w": 0.16, "h": 0.06, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": { "content": "Client", "role": "label", "align": "center" }
        },
        {
          "id": "server",
          "kind": "shape",
          "transform": { "x": 0.78, "y": 0.5, "w": 0.18, "h": 0.16, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": { "shape": "rect", "filled": true, "stroke": true }
        },
        {
          "id": "server_label",
          "kind": "text",
          "transform": { "x": 0.78, "y": 0.5, "w": 0.16, "h": 0.06, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": { "content": "Server", "role": "label", "align": "center" }
        },
        {
          "id": "link",
          "kind": "arrow",
          "transform": { "x": 0.5, "y": 0.45, "w": 0.3, "h": 0.05, "anchor": "center" },
          "z_index": 1,
          "visible": true,
          "opacity": 1,
          "props": {
            "from": { "object_id": "client" },
            "to": { "object_id": "server" },
            "head": "both",
            "label": "HTTP"
          }
        },
        {
          "id": "packet",
          "kind": "packet",
          "transform": { "x": 0.30, "y": 0.40, "w": 0.08, "h": 0.05, "anchor": "center" },
          "z_index": 4,
          "visible": true,
          "opacity": 1,
          "props": { "label": "REQ", "path_object_id": "link", "payload": "GET /" }
        }
      ],
      "animations": [
        {
          "id": "send_req",
          "target_object_id": "packet",
          "preset": "follow_path",
          "time_unit": "normalized",
          "t": [0.2, 0.5],
          "easing": "ease_in_out",
          "params": { "path_object_id": "link", "label_to": "REQ" }
        },
        {
          "id": "send_res",
          "target_object_id": "packet",
          "preset": "follow_path",
          "time_unit": "normalized",
          "t": [0.55, 0.85],
          "easing": "ease_in_out",
          "params": { "path_object_id": "link", "reverse": true, "label_to": "RES" }
        }
      ],
      "camera": {
        "preset": "full_stage",
        "initial": { "x": 0.5, "y": 0.5, "zoom": 1.0 },
        "keyframes": []
      },
      "duration": { "mode": "from_narration", "hint_sec": 11 }
    }
  ]
}
```

---

### 25.5 Historical / Process Timeline

**Visual mode:** `timeline_events`

```json
{
  "scenes": [
    {
      "id": "scene_www_timeline",
      "order": 0,
      "purpose": "Place key events of the early Web on a timeline",
      "visual_mode": "timeline_events",
      "narration_beat_ids": ["nar_tl"],
      "background": { "type": "solid", "color": "#FAFAF9" },
      "objects": [
        {
          "id": "title",
          "kind": "text",
          "transform": { "x": 0.5, "y": 0.12, "w": 0.8, "h": 0.08, "anchor": "center" },
          "z_index": 1,
          "visible": true,
          "opacity": 1,
          "props": { "content": "Early Web Timeline", "role": "title", "align": "center" }
        },
        {
          "id": "track",
          "kind": "timeline_track",
          "transform": { "x": 0.5, "y": 0.55, "w": 0.82, "h": 0.22, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "props": {
            "orientation": "horizontal",
            "active_event_id": "ev_1991",
            "events": [
              { "id": "ev_1989", "label": "1989", "t": 0.15, "description": "Proposal" },
              { "id": "ev_1991", "label": "1991", "t": 0.45, "description": "Public WWW" },
              { "id": "ev_1993", "label": "1993", "t": 0.75, "description": "Mosaic" }
            ]
          }
        }
      ],
      "animations": [
        {
          "id": "activate_1991",
          "target_object_id": "track",
          "preset": "state_set",
          "time_unit": "normalized",
          "t": [0.4, 0.55],
          "params": { "prop": "active_event_id", "value": "ev_1991" }
        }
      ],
      "camera": {
        "preset": "focus_object",
        "initial": { "x": 0.5, "y": 0.55, "zoom": 1.0 },
        "keyframes": [
          {
            "id": "cam_event",
            "t": 0.4,
            "time_unit": "normalized",
            "transform": { "x": 0.5, "y": 0.55, "zoom": 1.15 },
            "focus_object_id": "track",
            "easing": "ease_in_out"
          }
        ]
      },
      "duration": { "mode": "from_narration", "hint_sec": 16 }
    }
  ]
}
```

---

### 25.6 Programming / Code Walkthrough

**Visual mode:** `code_walkthrough`

```json
{
  "scenes": [
    {
      "id": "scene_code",
      "order": 0,
      "purpose": "Explain the mid index calculation line in binary search code",
      "visual_mode": "code_walkthrough",
      "narration_beat_ids": ["nar_code"],
      "background": { "type": "solid", "color": "#0F172A" },
      "objects": [
        {
          "id": "title",
          "kind": "text",
          "transform": { "x": 0.5, "y": 0.1, "w": 0.8, "h": 0.07, "anchor": "center" },
          "z_index": 1,
          "visible": true,
          "opacity": 1,
          "style_tokens": ["title"],
          "props": { "content": "mid = lo + (hi - lo) // 2", "role": "title", "align": "center" }
        },
        {
          "id": "code",
          "kind": "code_block",
          "transform": { "x": 0.5, "y": 0.52, "w": 0.76, "h": 0.48, "anchor": "center" },
          "z_index": 2,
          "visible": true,
          "opacity": 1,
          "style_tokens": ["code"],
          "props": {
            "language": "python",
            "lines": [
              "def binary_search(arr, target):",
              "    lo, hi = 0, len(arr) - 1",
              "    while lo <= hi:",
              "        mid = lo + (hi - lo) // 2",
              "        if arr[mid] == target:",
              "            return mid",
              "        if arr[mid] < target:",
              "            lo = mid + 1",
              "        else:",
              "            hi = mid - 1",
              "    return -1"
            ],
            "highlight_lines": [4],
            "focus_line": 4
          }
        },
        {
          "id": "note",
          "kind": "label_callout",
          "transform": { "x": 0.82, "y": 0.36, "w": 0.2, "h": 0.12, "anchor": "center" },
          "z_index": 3,
          "visible": true,
          "opacity": 1,
          "props": {
            "text": "Avoids overflow-style mid calc habit",
            "target_object_id": "code",
            "placement": "e"
          }
        }
      ],
      "animations": [
        {
          "id": "focus_mid_line",
          "target_object_id": "code",
          "preset": "highlight_set",
          "time_unit": "normalized",
          "t": [0.2, 0.4],
          "params": { "lines": [4] }
        },
        {
          "id": "fade_note",
          "target_object_id": "note",
          "preset": "fade_in",
          "time_unit": "normalized",
          "t": [0.45, 0.6]
        }
      ],
      "camera": {
        "preset": "focus_object",
        "initial": { "x": 0.5, "y": 0.52, "zoom": 1.0 },
        "keyframes": [
          {
            "id": "cam_code",
            "t": 0.2,
            "time_unit": "normalized",
            "transform": { "x": 0.5, "y": 0.52, "zoom": 1.25 },
            "focus_object_id": "code",
            "easing": "ease_in_out"
          }
        ]
      },
      "duration": { "mode": "from_narration", "hint_sec": 18 }
    }
  ]
}
```

---

## 26. Anti-Patterns

| Anti-Pattern | Why Forbidden |
|--------------|---------------|
| Embedding raw LLM prompts in scenes | Breaks determinism; renderer must not need AI |
| One generative image per scene as default | Violates diagram-first constitution |
| Using pixel coordinates mixed with normalized without declaring space | Breaks resolution independence |
| Mutating another agent’s artifact in place | Breaks isolation & caching |
| Putting narration text only inside images | Destroys subtitles/TTS sync |
| Renderer calling Script Agent when text missing | Violates renderer contract |
| Theme colors hardcoded in every object prop | Prevents theme switching |
| Timeline without scene markers | Hurts resume/debug/chaptering |

---

## 27. Normative Glossary

| Term | Definition |
|------|------------|
| Presentation DSL | Versioned JSON language describing the internal presentation |
| Scene Graph | Object tree/list with transforms and kinds derived from DSL scenes |
| Timeline | Absolute-time tracks binding scenes, animation, camera, audio, subtitles |
| Kind | Object type discriminator (`array`, `arrow`, …) |
| Style token | Semantic style key resolved by theme |
| Beat | Narration unit with ID and text |
| Compile | Plans → DSL objects/layout |
| Bind | DSL + media durations → timeline |
| Render-ready | Validation + bind complete; renderer may run |

---

## 28. Appendix: Complete Field Index

Quick index of top-level and major nested objects. Details are in sections above.

| Path | Section |
|------|---------|
| `dsl_version` | §21 |
| `project.*` | §4 |
| `metadata.*` | §5 |
| `theme.*` | §6 |
| `assets[]` | §7 |
| `voice.*` | §8 |
| `subtitles.*` | §9 |
| `layout_defaults.*` | §10 |
| `scenes[]` | §11 |
| `scenes[].background` | §12 |
| `scenes[].layout` | §10 |
| `scenes[].objects[]` | §13–14 |
| `scenes[].animations[]` | §15 |
| `scenes[].camera` | §16 |
| `scenes[].duration` | §18 |
| `scenes[].transitions` | §11 |
| `timeline.*` | §17 |
| `extensions.*` | §22 |

---

## Closing Statement

The Presentation DSL is the **official language of ExplainX**.

It is how intelligence becomes structure, how structure becomes motion, and how motion becomes video — without ever requiring the renderer to think.

```
Agents plan.
The DSL records.
Engines compile time.
The renderer paints.
```

All future agents, engines, plugins, and Cursor prompts must treat this document as the linguistic constitution of the system.

---

*End of PRESENTATION_DSL.md*  
*ExplainX Engineering — One Language. Many Agents. Deterministic Pictures.*
