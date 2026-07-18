# Asset Ontology

**Schema version:** `1.0.0`  
**Module:** `asset_intelligence.schemas.asset`

## Responsibility

Describe every *reusable educational visual* as structured metadata — independent of file bytes and generation backends.

## Core types

### `AssetOntologyEntry` (what kind of thing)

| Field | Meaning |
|-------|---------|
| `concept` | Human/educational concept name (e.g. Earth) |
| `category` | `AssetCategory` enum |
| `subcategory` | Optional finer grain |
| `tags` | Free-form search tags |
| `style_id` | Preferred / bound style (optional) |
| `view` | `front` \| `side` \| `top` \| `cross_section` \| `isometric` \| `schematic` |
| `difficulty` | Pedagogy level |
| `subject` | Curriculum subject |
| `dependencies` | Other concept/asset names required |

### `AssetRecord` (library identity)

| Field | Meaning |
|-------|---------|
| `asset_id` | UUID |
| `content_hash` | SHA of pixels/file when present |
| `semantic_name` | Stable name for reuse lookup |
| `style_id` | HOW this variant was styled |
| `scope` | `global` \| `project` \| `derived` |
| `version` | Asset version string |
| `usage_count` | Reuse telemetry |
| `parent_asset_id` / `variant_of` | Derivation / variants |
| `metadata` | Extensible bag |
| `created_at` / `updated_at` | Audit |

## Category taxonomy (extensible)

```text
planet | organ | cell | neuron | battery | machine_part
molecule | historical_figure | map | timeline | equation
icon | arrow | diagram | background | other
```

Examples map naturally:

| Example | Category |
|---------|----------|
| Planet / Earth | `planet` |
| Heart | `organ` |
| Neuron | `neuron` |
| Battery | `battery` |
| Gear | `machine_part` |
| H₂O | `molecule` |
| Newton | `historical_figure` |
| World map | `map` |
| Timeline | `timeline` |
| E=mc² | `equation` |
| Play icon | `icon` |
| Force arrow | `arrow` |

## Ontology vs Concept Graph

```text
Concept Graph  →  educational meaning & relationships
Asset Ontology →  how that meaning becomes a reusable visual type
Asset Record   →  one concrete (or planned) library entry
```

## Extension points

1. Add `AssetCategory` members without changing planner APIs.
2. Store domain-specific fields under `metadata` until promoted to schema v2.
3. Link ontology `dependencies` to concept graph `REQUIRES` / `CONTAINS` edges.
