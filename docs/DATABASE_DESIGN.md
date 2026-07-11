# ExplainX — Database Design

**Document Status:** Canonical Data Architecture Reference  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Primary Engine (V1):** SQLite 3  
**Future Target:** PostgreSQL (via Storage Port; business logic unchanged)  
**Companions:**  
[`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`PRESENTATION_DSL.md`](./PRESENTATION_DSL.md) ·  
[`AGENT_SPECIFICATIONS.md`](./AGENT_SPECIFICATIONS.md)  

> **Authority:** This document defines how ExplainX persists relational state.  
> Large binaries and stage JSON artifacts live on the **filesystem**; SQLite stores **registry, relationships, job state, and pointers**.  
> Application services must access persistence through the **Storage Port / Repository layer**, never via ad-hoc SQL scattered in agents.

---

## Table of Contents

1. [Design Goals](#1-design-goals)
2. [Storage Strategy Overview](#2-storage-strategy-overview)
3. [Why SQLite in Version 1](#3-why-sqlite-in-version-1)
4. [PostgreSQL Migration Path](#4-postgresql-migration-path)
5. [Logical Data Domains](#5-logical-data-domains)
6. [Naming & Type Conventions](#6-naming--type-conventions)
7. [Complete ER Diagram](#7-complete-er-diagram)
8. [Table Specifications](#8-table-specifications)
9. [Relationships Summary](#9-relationships-summary)
10. [Indexing Strategy](#10-indexing-strategy)
11. [Filesystem ↔ Database Mapping](#11-filesystem--database-mapping)
12. [Project Versioning](#12-project-versioning)
13. [Backup Strategy](#13-backup-strategy)
14. [Migration Strategy](#14-migration-strategy)
15. [Integrity, Concurrency & Transactions](#15-integrity-concurrency--transactions)
16. [Security & Privacy Considerations](#16-security--privacy-considerations)
17. [Appendix A: DDL Sketch (Informative)](#17-appendix-a-ddl-sketch-informative)
18. [Appendix B: Example Rows](#18-appendix-b-example-rows)

---

## 1. Design Goals

| Goal | Requirement |
|------|-------------|
| Local-first | Single-file DB works offline on Windows laptops |
| Artifact-centric | DB points at JSON/media files; does not embed Presentation DSL blobs as opaque undocumented text without versioning |
| Job-resumable | Render/pipeline jobs checkpointable via relational state |
| Portable business logic | Repositories abstract SQL dialect differences |
| Auditable | Created/updated timestamps, status enums, version rows |
| Lightweight | Fit i7-1255U / 16GB class machines; avoid heavy DB servers in V1 |

### 1.1 What Belongs in SQLite

- Projects, settings, themes registry  
- Jobs / stages / attempts  
- Indexes of scenes, narrations, subtitles, videos, assets (metadata + paths)  
- Languages, plugin enablement  
- Cache keys, version history pointers  
- Export manifests (metadata)  

### 1.2 What Belongs on the Filesystem

- Source uploads (PDF/DOCX/MD/…)  
- Agent artifacts (`knowledge.json`, `script.json`, …)  
- `presentation.dsl.json`, `timeline.json`  
- Audio WAV/MP3, SRT/VTT, MP4, thumbnails  
- Theme pack files, icon packs, model binaries (outside project tree)  

---

## 2. Storage Strategy Overview

```
data/
├── explainx.db                 # SQLite database (or configurable path)
├── explainx.db-wal             # WAL file (when WAL mode enabled)
├── explainx.db-shm
├── projects/
│   └── {project_id}/
│       ├── source/
│       ├── artifacts/
│       ├── export/
│       ├── logs/
│       └── project.json        # optional mirror of core project fields
├── cache/
│   └── artifact_cache/         # content-addressed optional cache
├── models/                     # Ollama/Piper references (paths in settings)
└── backups/
    └── ...
```

### 2.1 Dual-Write Principle

For critical project fields:

1. **SQLite** is the source of truth for status, listing, and relations.  
2. **Filesystem artifacts** are the source of truth for large stage payloads.  
3. Optional `project.json` mirror may exist for human debugging; if conflict, SQLite status wins for app behavior, artifact files win for content regeneration.

### 2.2 Path Storage Rules

- Store paths **relative to project root** when inside a project (`artifacts/voice/nar_01.wav`).  
- Store paths relative to app data root for global assets (`assets/openmoji/sun.svg`) or absolute only in settings for external model dirs.  
- Never store secrets in the database.

---

## 3. Why SQLite in Version 1

| Reason | Detail |
|--------|--------|
| Zero ops | No separate DB server for offline desktop use |
| Single file | Easy backup/copy with project data |
| Sufficient concurrency | V1 defaults to one active heavy job; WAL covers readers |
| Embedded | Ships with Python; predictable on Windows |
| Cost / offline | Aligns with 100% free, offline-first constitution |
| Good enough scale | Thousands of local projects ≪ SQLite limits |

SQLite is an intentional **product** choice for V1, not a lack of architecture.

---

## 4. PostgreSQL Migration Path

### 4.1 Abstraction Rule

```
Agents / Services
        │
        ▼
  Repository Interfaces (Storage Port)
        │
        ├──────────────┬────────────────┐
        ▼              ▼                ▼
  SQLiteAdapter   PostgresAdapter   (Future)
```

Business logic (agents, orchestrator, API) MUST depend on repositories such as:

- `ProjectRepository`  
- `JobRepository`  
- `AssetRepository`  
- `SceneRepository`  
- `RenderJobRepository`  
- …

**Not** on raw SQLite APIs.

### 4.2 What Changes for PostgreSQL

| Concern | SQLite V1 | PostgreSQL Future |
|---------|-----------|-------------------|
| Connection | File path | Host/DB/user/ssl |
| IDs | TEXT UUID | UUID or TEXT |
| JSON | TEXT / JSON1 | JSONB |
| Booleans | INTEGER 0/1 | BOOLEAN |
| Timestamps | TEXT ISO-8601 | TIMESTAMPTZ |
| Upserts | `ON CONFLICT` | `ON CONFLICT` |
| Full text | Optional FTS5 | tsvector |
| Concurrency | WAL + busy timeout | MVCC |

### 4.3 What Does Not Change

- Table names and logical columns (keep aligned)  
- Foreign key relationships  
- Status enums and job state machine  
- Filesystem layout for media (unless moving to object storage later)  
- Agent contracts and Presentation DSL  

### 4.4 Migration Approach (When Needed)

1. Keep schema migrations dialect-aware (Alembic or equivalent).  
2. Export SQLite → staging → Postgres via ETL script.  
3. Switch config `DATABASE_URL`.  
4. Run verification queries (counts, FK integrity).  
5. Filesystem project blobs remain as-is or sync to object storage behind the same path interface.

---

## 5. Logical Data Domains

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Identity   │   │  Content    │   │  Pipeline   │
│  projects   │──▶│  scenes     │──▶│  render_jobs│
│  settings   │   │  narrations │   │  job_stages │
└─────────────┘   │  subtitles  │   │  cache_entries
                  │  videos     │   └─────────────┘
                  │  assets     │
                  │  metadata   │
                  └─────────────┘
┌─────────────┐   ┌─────────────┐
│  Catalog    │   │  Versioning │
│  themes     │   │  project_versions
│  languages  │   │  artifact_index
└─────────────┘   └─────────────┘
```

---

## 6. Naming & Type Conventions

| Convention | Rule |
|------------|------|
| Table names | `snake_case`, plural |
| Primary keys | `{table_singular}_id` TEXT UUID (except pure lookup tables may use stable string codes) |
| Foreign keys | `{referenced_singular}_id` |
| Booleans | INTEGER `0/1` in SQLite |
| Enums | TEXT with CHECK constraints |
| Timestamps | TEXT ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) |
| Soft delete | `deleted_at` NULL = active |
| JSON columns | TEXT containing JSON (validate in app); document schema version |

---

## 7. Complete ER Diagram

```
┌──────────────────┐       ┌──────────────────┐
│     themes       │       │    languages     │
│ PK theme_id      │       │ PK language_code │
└────────┬─────────┘       └────────┬─────────┘
         │                          │
         │                          │
         ▼                          ▼
┌──────────────────────────────────────────────┐
│                   projects                    │
│ PK project_id                                 │
│ FK theme_id → themes                          │
│ FK source_language_code → languages           │
│ FK target_language_code → languages           │
└───────┬─────────────────┬───────────┬─────────┘
        │                 │           │
        │                 │           │
        ▼                 ▼           ▼
┌───────────────┐  ┌─────────────┐  ┌────────────────────┐
│ project_      │  │  metadata   │  │ project_versions   │
│ settings      │  │ PK metadata │  │ PK project_version │
│ PK ...        │  │    _id      │  │    _id             │
│ FK project_id │  │ FK project  │  │ FK project_id      │
└───────────────┘  └─────────────┘  └─────────┬──────────┘
                                              │
        ┌─────────────────────────────────────┼──────────────────────┐
        │                                     │                      │
        ▼                                     ▼                      ▼
┌───────────────┐                    ┌─────────────────┐    ┌────────────────┐
│    scenes     │                    │ artifact_index  │    │  render_jobs   │
│ PK scene_id   │                    │ PK artifact_id  │    │ PK render_job  │
│ FK project_id │                    │ FK project_id   │    │    _id         │
│ FK project_   │                    │ FK project_     │    │ FK project_id  │
│    version_id │                    │    version_id   │    │ FK project_    │
└───────┬───────┘                    └─────────────────┘    │    version_id  │
        │                                                   └───────┬────────┘
        │                                                           │
        ├──────────────────┬──────────────────┐                     ▼
        ▼                  ▼                  ▼            ┌────────────────┐
┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │  job_stages    │
│  narrations   │  │  subtitles    │  │ scene_assets  │   │ PK job_stage   │
│ PK narration  │  │ PK subtitle   │  │ PK ...        │   │    _id         │
│    _id        │  │    _id        │  │ FK scene_id   │   │ FK render_job  │
│ FK scene_id   │  │ FK scene_id   │  │ FK asset_id   │   │    _id         │
│ FK project_id │  │ FK project_id │  └───────┬───────┘   └────────────────┘
└───────────────┘  └───────────────┘          │
                                              ▼
                                     ┌────────────────┐
                                     │    assets      │
                                     │ PK asset_id    │
                                     │ FK project_id  │
                                     │    (nullable   │
                                     │     for global)│
                                     └────────────────┘

┌──────────────────┐
│     videos       │
│ PK video_id      │
│ FK project_id    │
│ FK render_job_id │
│ FK project_      │
│    version_id    │
└──────────────────┘

┌──────────────────┐       ┌──────────────────┐
│ cache_entries    │       │ app_settings     │
│ PK cache_key     │       │ PK setting_key   │
└──────────────────┘       └──────────────────┘

┌──────────────────┐       ┌──────────────────┐
│ plugins          │       │ schema_migrations│
│ PK plugin_id     │       │ PK version       │
└──────────────────┘       └──────────────────┘
```

### 7.1 Crow’s Foot (Textual)

```
themes 1 ──────── < projects
languages 1 ──── < projects (source)
languages 1 ──── < projects (target)
projects 1 ────── < project_versions
projects 1 ────── < scenes
projects 1 ────── < narrations
projects 1 ────── < subtitles
projects 1 ────── < assets
projects 1 ────── < videos
projects 1 ────── < render_jobs
projects 1 ────── 1 metadata
projects 1 ────── 1 project_settings
projects 1 ────── < artifact_index
project_versions 1 ── < scenes
project_versions 1 ── < render_jobs
project_versions 1 ── < videos
project_versions 1 ── < artifact_index
scenes 1 ──────── < narrations
scenes 1 ──────── < subtitles
scenes M ──────── M assets (via scene_assets)
render_jobs 1 ─── < job_stages
render_jobs 1 ─── < videos
```

---

## 8. Table Specifications

Each field lists: name, type (SQLite), nullability, description.

---

### 8.1 `projects`

Core project registry.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `project_id` | TEXT | NO | **PK**. UUID |
| `title` | TEXT | NO | Display title |
| `description` | TEXT | YES | Short description |
| `status` | TEXT | NO | `draft` \| `queued` \| `running` \| `completed` \| `failed` \| `cancelled` \| `archived` |
| `source_type` | TEXT | NO | `pdf` \| `docx` \| `txt` \| `md` \| `topic` |
| `source_path` | TEXT | YES | Relative path to source file; NULL if topic-only |
| `source_topic` | TEXT | YES | Topic string when `source_type=topic` |
| `source_hash` | TEXT | NO | Hash of source content |
| `theme_id` | TEXT | NO | **FK → themes.theme_id** |
| `source_language_code` | TEXT | NO | **FK → languages.language_code** |
| `target_language_code` | TEXT | NO | **FK → languages.language_code** |
| `voice_id` | TEXT | YES | Piper voice id |
| `difficulty` | TEXT | YES | `beginner` \| `intermediate` \| `advanced` |
| `current_version_id` | TEXT | YES | **FK → project_versions.project_version_id** (nullable until first version) |
| `dsl_path` | TEXT | YES | Relative path to Presentation DSL |
| `timeline_path` | TEXT | YES | Relative path to timeline artifact |
| `project_root` | TEXT | NO | Relative path `projects/{id}` |
| `estimated_duration_sec` | REAL | YES | From metadata agent |
| `actual_duration_sec` | REAL | YES | After timeline bind |
| `error_code` | TEXT | YES | Last terminal error |
| `error_message` | TEXT | YES | Last terminal error detail |
| `created_at` | TEXT | NO | ISO-8601 UTC |
| `updated_at` | TEXT | NO | ISO-8601 UTC |
| `completed_at` | TEXT | YES | When status became completed |
| `deleted_at` | TEXT | YES | Soft delete timestamp |

**Primary key:** `project_id`  
**Foreign keys:**  
- `theme_id` → `themes(theme_id)`  
- `source_language_code` → `languages(language_code)`  
- `target_language_code` → `languages(language_code)`  
- `current_version_id` → `project_versions(project_version_id)` DEFERRABLE / set after version insert  

**Checks:** status/source_type/difficulty enums.

---

### 8.2 `project_settings`

Per-project generation/export settings (1:1 with projects).

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `project_id` | TEXT | NO | **PK, FK → projects.project_id** ON DELETE CASCADE |
| `export_width` | INTEGER | NO | e.g. 1280 |
| `export_height` | INTEGER | NO | e.g. 720 |
| `fps` | REAL | NO | e.g. 30 |
| `quality_profile` | TEXT | NO | `draft` \| `standard` \| `high` |
| `burn_in_subtitles` | INTEGER | NO | 0/1 |
| `subtitle_formats` | TEXT | NO | JSON array string `["srt","vtt"]` |
| `speaking_rate` | REAL | NO | Default 1.0 |
| `max_scenes` | INTEGER | YES | Optional cap |
| `plugin_flags` | TEXT | YES | JSON object of enabled plugins |
| `extra_json` | TEXT | YES | Forward-compatible settings JSON |
| `updated_at` | TEXT | NO | |

**Primary key:** `project_id`  
**Foreign keys:** `project_id` → `projects(project_id)`

---

### 8.3 `project_versions`

Immutable (append-only) snapshots of a project generation lineage.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `project_version_id` | TEXT | NO | **PK**. UUID |
| `project_id` | TEXT | NO | **FK → projects.project_id** |
| `version_number` | INTEGER | NO | Monotonic per project starting at 1 |
| `label` | TEXT | YES | Optional `v1`, `theme-dark-retry` |
| `parent_version_id` | TEXT | YES | **FK → project_versions.project_version_id** |
| `change_reason` | TEXT | YES | `initial` \| `theme_change` \| `voice_change` \| `full_regen` \| `manual` |
| `config_hash` | TEXT | NO | Hash of settings relevant to generation |
| `source_hash` | TEXT | NO | Source content hash at this version |
| `graph_version` | TEXT | NO | Orchestrator graph version |
| `dsl_version` | TEXT | YES | Presentation DSL version used |
| `dsl_path` | TEXT | YES | Versioned DSL path |
| `timeline_path` | TEXT | YES | Versioned timeline path |
| `artifact_root` | TEXT | NO | e.g. `artifacts/v3/` |
| `status` | TEXT | NO | `open` \| `sealed` \| `superseded` |
| `created_at` | TEXT | NO | |
| `sealed_at` | TEXT | YES | When marked immutable |

**Primary key:** `project_version_id`  
**Unique:** (`project_id`, `version_number`)  
**Foreign keys:**  
- `project_id` → `projects`  
- `parent_version_id` → `project_versions`  

---

### 8.4 `metadata`

Educational/catalog metadata (1:1 with project; version-aware copy may also live in files).

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `metadata_id` | TEXT | NO | **PK**. UUID |
| `project_id` | TEXT | NO | **FK → projects.project_id** UNIQUE |
| `project_version_id` | TEXT | YES | **FK → project_versions** (row reflects this version) |
| `title` | TEXT | NO | |
| `description` | TEXT | NO | |
| `tags_json` | TEXT | NO | JSON string array |
| `domain` | TEXT | YES | Primary domain |
| `subtopics_json` | TEXT | YES | JSON array |
| `difficulty` | TEXT | YES | |
| `learning_objectives_json` | TEXT | YES | JSON array |
| `prerequisites_json` | TEXT | YES | JSON array |
| `thumbnail_path` | TEXT | YES | Relative export/thumb path |
| `thumbnail_scene_id` | TEXT | YES | Preferred scene |
| `estimated_duration_sec` | REAL | YES | |
| `actual_duration_sec` | REAL | YES | |
| `locale_source` | TEXT | YES | |
| `locale_target` | TEXT | YES | |
| `extra_json` | TEXT | YES | Extension bag |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `metadata_id`  
**Foreign keys:** `project_id` → `projects`; `project_version_id` → `project_versions`  
**Unique:** `project_id`

---

### 8.5 `scenes`

Indexed scene rows derived from Scene Plan / DSL (for querying; full object graph remains in DSL file).

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `scene_id` | TEXT | NO | **PK**. Logical scene id (e.g. `scene_intro`) scoped with project in unique key |
| `project_id` | TEXT | NO | **FK → projects** |
| `project_version_id` | TEXT | NO | **FK → project_versions** |
| `order_index` | INTEGER | NO | 0-based order |
| `purpose` | TEXT | NO | Learning purpose |
| `visual_mode` | TEXT | NO | DSL visual_mode enum |
| `duration_hint_sec` | REAL | YES | |
| `duration_resolved_sec` | REAL | YES | After timeline bind |
| `start_sec` | REAL | YES | Absolute start on timeline |
| `end_sec` | REAL | YES | Absolute end |
| `background_type` | TEXT | YES | Denormalized for filters |
| `object_count` | INTEGER | YES | Stats |
| `dsl_scene_path` | TEXT | YES | Optional excerpt path; usually in main DSL |
| `status` | TEXT | NO | `planned` \| `compiled` \| `timed` \| `rendered` \| `failed` |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** composite recommended — see note.

**Normative PK strategy (V1):**

Use surrogate:

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `scene_row_id` | TEXT | NO | **PK**. UUID |

And enforce:

**Unique:** (`project_version_id`, `scene_id`)  
**Unique:** (`project_version_id`, `order_index`)

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `scene_row_id` | TEXT | NO | **PK** UUID |
| `scene_id` | TEXT | NO | Logical id inside DSL |
| … | … | … | (remaining fields as above) |

**Foreign keys:** `project_id` → `projects`; `project_version_id` → `project_versions`

---

### 8.6 `narrations`

Narration beats / voice units.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `narration_id` | TEXT | NO | **PK**. UUID |
| `beat_id` | TEXT | NO | Logical beat id (`nar_01`) |
| `project_id` | TEXT | NO | **FK → projects** |
| `project_version_id` | TEXT | NO | **FK → project_versions** |
| `scene_row_id` | TEXT | YES | **FK → scenes.scene_row_id** |
| `scene_id` | TEXT | YES | Logical scene id denorm |
| `language_code` | TEXT | NO | **FK → languages** |
| `text` | TEXT | NO | Spoken text |
| `text_source` | TEXT | YES | Pre-translation text if translated |
| `audio_path` | TEXT | YES | Relative WAV/MP3 path |
| `audio_hash` | TEXT | YES | |
| `duration_sec` | REAL | YES | Measured TTS duration |
| `start_sec` | REAL | YES | Absolute timeline start |
| `end_sec` | REAL | YES | Absolute timeline end |
| `voice_id` | TEXT | YES | Voice used for this beat |
| `speaking_rate` | REAL | YES | |
| `order_index` | INTEGER | NO | Global or scene order |
| `status` | TEXT | NO | `draft` \| `synthesized` \| `failed` |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `narration_id`  
**Unique:** (`project_version_id`, `beat_id`)  
**Foreign keys:** project, version, scene_row, language  

---

### 8.7 `subtitles`

Subtitle cues (and/or file-level rows). V1 stores cues relationally for search/debug; files remain authoritative for export.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `subtitle_id` | TEXT | NO | **PK**. UUID |
| `cue_id` | TEXT | NO | Logical cue id |
| `project_id` | TEXT | NO | **FK → projects** |
| `project_version_id` | TEXT | NO | **FK → project_versions** |
| `scene_row_id` | TEXT | YES | **FK → scenes** |
| `narration_id` | TEXT | YES | **FK → narrations** |
| `language_code` | TEXT | NO | **FK → languages** |
| `text` | TEXT | NO | Cue text |
| `start_sec` | REAL | NO | |
| `end_sec` | REAL | NO | |
| `srt_path` | TEXT | YES | Shared file path (denormalized) |
| `vtt_path` | TEXT | YES | Shared file path |
| `burn_in` | INTEGER | NO | 0/1 intent at generation time |
| `order_index` | INTEGER | NO | |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `subtitle_id`  
**Unique:** (`project_version_id`, `cue_id`)  
**Check:** `end_sec > start_sec`  
**Foreign keys:** project, version, scene, narration, language  

#### 8.7.1 `subtitle_files` (optional companion table)

For file-level tracking without cue explosion in queries:

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `subtitle_file_id` | TEXT | NO | **PK** |
| `project_id` | TEXT | NO | **FK** |
| `project_version_id` | TEXT | NO | **FK** |
| `language_code` | TEXT | NO | **FK** |
| `format` | TEXT | NO | `srt` \| `vtt` |
| `path` | TEXT | NO | |
| `hash` | TEXT | YES | |
| `cue_count` | INTEGER | YES | |
| `created_at` | TEXT | NO | |

---

### 8.8 `assets`

Asset registry (project-local and global).

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `asset_id` | TEXT | NO | **PK**. UUID or stable logical id |
| `project_id` | TEXT | YES | **FK → projects**; NULL = global/shared |
| `project_version_id` | TEXT | YES | **FK**; NULL for global |
| `logical_key` | TEXT | NO | DSL asset id (`icon_sun`) |
| `asset_type` | TEXT | NO | `svg` \| `png` \| `jpg` \| `webp` \| `font` \| `audio` \| `procedural` \| `icon_ref` |
| `source` | TEXT | NO | `lucide` \| `openmoji` \| `undraw` \| `project` \| `procedural.*` \| `plugin.*` |
| `source_key` | TEXT | YES | Pack key |
| `path` | TEXT | YES | Resolved path |
| `hash` | TEXT | YES | Content hash |
| `license` | TEXT | YES | |
| `width` | REAL | YES | |
| `height` | REAL | YES | |
| `generator_name` | TEXT | YES | Procedural generator |
| `generator_params_json` | TEXT | YES | |
| `plugin_id` | TEXT | YES | **FK → plugins** optional |
| `status` | TEXT | NO | `resolved` \| `missing` \| `fallback` |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `asset_id`  
**Unique (project assets):** (`project_version_id`, `logical_key`) WHERE project_version_id NOT NULL  
**Foreign keys:** project, version, plugin  

---

### 8.9 `scene_assets`

Many-to-many: scenes ↔ assets.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `scene_asset_id` | TEXT | NO | **PK**. UUID |
| `scene_row_id` | TEXT | NO | **FK → scenes.scene_row_id** |
| `asset_id` | TEXT | NO | **FK → assets.asset_id** |
| `object_id` | TEXT | YES | DSL object using the asset |
| `usage_role` | TEXT | YES | `icon` \| `background` \| `illustration` \| `procedural` |
| `created_at` | TEXT | NO | |

**Primary key:** `scene_asset_id`  
**Unique:** (`scene_row_id`, `asset_id`, `object_id`)  
**Foreign keys:** scene_row, asset  

---

### 8.10 `videos`

Rendered / exported video outputs.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `video_id` | TEXT | NO | **PK**. UUID |
| `project_id` | TEXT | NO | **FK → projects** |
| `project_version_id` | TEXT | NO | **FK → project_versions** |
| `render_job_id` | TEXT | YES | **FK → render_jobs** |
| `path` | TEXT | NO | Relative MP4 path |
| `hash` | TEXT | YES | File hash |
| `width` | INTEGER | NO | |
| `height` | INTEGER | NO | |
| `fps` | REAL | NO | |
| `duration_sec` | REAL | YES | |
| `bitrate_kbps` | INTEGER | YES | |
| `codec_video` | TEXT | YES | e.g. `h264` |
| `codec_audio` | TEXT | YES | e.g. `aac` |
| `quality_profile` | TEXT | NO | |
| `thumbnail_path` | TEXT | YES | |
| `file_size_bytes` | INTEGER | YES | |
| `is_primary` | INTEGER | NO | 1 = current downloadable video |
| `status` | TEXT | NO | `processing` \| `ready` \| `failed` \| `deleted` |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `video_id`  
**Foreign keys:** project, version, render_job  

---

### 8.11 `themes`

Installed / bundled theme registry.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `theme_id` | TEXT | NO | **PK**. Stable id (`notebooklm`) |
| `name` | TEXT | NO | Display name |
| `version` | TEXT | NO | Theme pack version |
| `description` | TEXT | YES | |
| `pack_path` | TEXT | NO | Path to theme pack directory/file |
| `preview_path` | TEXT | YES | Preview image |
| `tokens_hash` | TEXT | YES | Hash of token file |
| `is_builtin` | INTEGER | NO | 0/1 |
| `is_enabled` | INTEGER | NO | 0/1 |
| `supports_rtl` | INTEGER | NO | 0/1 |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `theme_id`  

Seed rows (V1): `notebooklm`, `whiteboard`, `corporate`, `minimal`, `comic`, `dark`.

---

### 8.12 `languages`

Language catalog for UI and generation.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `language_code` | TEXT | NO | **PK**. BCP-47 (`en`, `hi`) |
| `name` | TEXT | NO | English name |
| `native_name` | TEXT | YES | |
| `tts_supported` | INTEGER | NO | 0/1 |
| `translation_supported` | INTEGER | NO | 0/1 |
| `default_voice_id` | TEXT | YES | |
| `is_enabled` | INTEGER | NO | 0/1 |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `language_code`

---

### 8.13 `render_jobs`

Pipeline / render job control plane.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `render_job_id` | TEXT | NO | **PK**. UUID |
| `project_id` | TEXT | NO | **FK → projects** |
| `project_version_id` | TEXT | YES | **FK → project_versions** |
| `job_type` | TEXT | NO | `full_pipeline` \| `render_only` \| `voice_only` \| `theme_rebind` \| `export_only` |
| `status` | TEXT | NO | `queued` \| `running` \| `completed` \| `failed` \| `cancelled` |
| `priority` | INTEGER | NO | Default 100 |
| `coarse_stage` | TEXT | YES | UI stage |
| `fine_stage` | TEXT | YES | Agent name |
| `progress_percent` | REAL | YES | Advisory 0–100 |
| `idempotency_key` | TEXT | YES | Prevent duplicate starts |
| `config_json` | TEXT | YES | Job-specific config snapshot |
| `input_hash` | TEXT | YES | |
| `attempt_count` | INTEGER | NO | Default 0 |
| `max_attempts` | INTEGER | NO | Default 3 |
| `error_code` | TEXT | YES | |
| `error_message` | TEXT | YES | |
| `checkpoint_json` | TEXT | YES | Last successful stage checkpoint summary |
| `worker_id` | TEXT | YES | Local worker identity |
| `queued_at` | TEXT | NO | |
| `started_at` | TEXT | YES | |
| `finished_at` | TEXT | YES | |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `render_job_id`  
**Unique:** `idempotency_key` WHERE NOT NULL  
**Foreign keys:** project, project_version  

> Naming note: despite `render_jobs`, this table tracks **all pipeline jobs**, including pre-render stages. Name retained for product vocabulary; `job_type` discriminates.

---

### 8.14 `job_stages`

Per-stage execution history for a job.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `job_stage_id` | TEXT | NO | **PK**. UUID |
| `render_job_id` | TEXT | NO | **FK → render_jobs** ON DELETE CASCADE |
| `stage_name` | TEXT | NO | e.g. `script_agent`, `timeline_agent` |
| `stage_order` | INTEGER | NO | |
| `status` | TEXT | NO | `pending` \| `running` \| `succeeded` \| `failed` \| `skipped` \| `cached` |
| `attempt` | INTEGER | NO | Attempt number |
| `cache_hit` | INTEGER | NO | 0/1 |
| `input_hash` | TEXT | YES | |
| `output_artifact_id` | TEXT | YES | Envelope id / path key |
| `output_path` | TEXT | YES | |
| `error_code` | TEXT | YES | |
| `error_message` | TEXT | YES | |
| `metrics_json` | TEXT | YES | duration_ms, token estimates, etc. |
| `started_at` | TEXT | YES | |
| `finished_at` | TEXT | YES | |
| `created_at` | TEXT | NO | |

**Primary key:** `job_stage_id`  
**Unique:** (`render_job_id`, `stage_name`, `attempt`)  
**Foreign keys:** `render_job_id` → `render_jobs`

---

### 8.15 `artifact_index`

Registry of filesystem artifacts for a project version.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `artifact_id` | TEXT | NO | **PK**. UUID |
| `project_id` | TEXT | NO | **FK → projects** |
| `project_version_id` | TEXT | NO | **FK → project_versions** |
| `artifact_type` | TEXT | NO | `raw_document` \| `knowledge_model` \| `narration_script` \| `presentation_dsl` \| `timeline` \| … |
| `schema_version` | TEXT | YES | |
| `producer_agent` | TEXT | YES | |
| `producer_version` | TEXT | YES | |
| `path` | TEXT | NO | Relative path |
| `content_hash` | TEXT | YES | |
| `input_hash` | TEXT | YES | Cache key input |
| `size_bytes` | INTEGER | YES | |
| `status` | TEXT | NO | `writing` \| `ready` \| `invalid` \| `deleted` |
| `created_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `artifact_id`  
**Unique:** (`project_version_id`, `artifact_type`, `content_hash`) optional soft unique — normative unique for “current” ready artifact:

**Unique partial (logical):** one `ready` row per (`project_version_id`, `artifact_type`) enforced in app or via filtered unique index if supported.

**Foreign keys:** project, version  

---

### 8.16 `cache_entries`

Global/stage cache index.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `cache_key` | TEXT | NO | **PK**. Hash string |
| `namespace` | TEXT | NO | e.g. `knowledge_agent`, `tts` |
| `project_id` | TEXT | YES | Optional scope |
| `path` | TEXT | NO | Cached payload path |
| `content_hash` | TEXT | YES | |
| `metadata_json` | TEXT | YES | |
| `hit_count` | INTEGER | NO | Default 0 |
| `created_at` | TEXT | NO | |
| `last_accessed_at` | TEXT | NO | |
| `expires_at` | TEXT | YES | |

**Primary key:** `cache_key`

---

### 8.17 `app_settings`

Application-global settings (key/value).

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `setting_key` | TEXT | NO | **PK** |
| `setting_value` | TEXT | NO | JSON or scalar string |
| `value_type` | TEXT | NO | `string` \| `number` \| `boolean` \| `json` |
| `updated_at` | TEXT | NO | |

Examples: `models.ollama_host`, `models.default_llm`, `storage.root`, `jobs.max_concurrent`.

---

### 8.18 `plugins`

Installed plugin registry.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `plugin_id` | TEXT | NO | **PK** |
| `name` | TEXT | NO | |
| `version` | TEXT | NO | |
| `plugin_type` | TEXT | NO | `theme` \| `asset_pack` \| `visual_backend` \| `tts` \| `renderer` \| `importer` |
| `entry` | TEXT | YES | Load entry reference |
| `is_enabled` | INTEGER | NO | 0/1 |
| `is_offline` | INTEGER | NO | 0/1 |
| `permissions_json` | TEXT | YES | |
| `installed_at` | TEXT | NO | |
| `updated_at` | TEXT | NO | |

**Primary key:** `plugin_id`

---

### 8.19 `schema_migrations`

Migration bookkeeping.

| Field | Type | Null | Description |
|-------|------|------|-------------|
| `version` | TEXT | NO | **PK**. Migration id e.g. `20260711_001` |
| `description` | TEXT | NO | |
| `applied_at` | TEXT | NO | |
| `checksum` | TEXT | YES | Migration file hash |

**Primary key:** `version`

---

## 9. Relationships Summary

| Parent | Child | Cardinality | On Delete (normative) |
|--------|-------|-------------|------------------------|
| themes | projects | 1:N | RESTRICT |
| languages | projects | 1:N | RESTRICT |
| projects | project_settings | 1:1 | CASCADE |
| projects | metadata | 1:1 | CASCADE |
| projects | project_versions | 1:N | CASCADE |
| projects | scenes | 1:N | CASCADE |
| projects | narrations | 1:N | CASCADE |
| projects | subtitles | 1:N | CASCADE |
| projects | assets | 1:N | CASCADE |
| projects | videos | 1:N | CASCADE |
| projects | render_jobs | 1:N | CASCADE |
| projects | artifact_index | 1:N | CASCADE |
| project_versions | scenes | 1:N | CASCADE |
| project_versions | narrations | 1:N | CASCADE |
| project_versions | videos | 1:N | CASCADE |
| project_versions | render_jobs | 1:N | SET NULL or RESTRICT |
| scenes | narrations | 1:N | SET NULL |
| scenes | subtitles | 1:N | SET NULL |
| scenes | scene_assets | 1:N | CASCADE |
| assets | scene_assets | 1:N | CASCADE |
| narrations | subtitles | 1:N | SET NULL |
| render_jobs | job_stages | 1:N | CASCADE |
| render_jobs | videos | 1:N | SET NULL |
| plugins | assets | 1:N | SET NULL |

---

## 10. Indexing Strategy

### 10.1 Principles

1. Index foreign keys used in joins.  
2. Index status columns used in queues/UI filters.  
3. Index (`project_id`, `updated_at`) for library sorting.  
4. Avoid over-indexing write-heavy stage tables beyond necessity.  
5. Use partial indexes for “current/primary” rows when helpful.

### 10.2 Required Indexes

| Index Name | Table | Columns | Purpose |
|------------|-------|---------|---------|
| `ix_projects_status` | projects | `status` | Filter active/failed |
| `ix_projects_updated_at` | projects | `updated_at DESC` | Library sort |
| `ix_projects_theme_id` | projects | `theme_id` | FK / filter |
| `ix_projects_deleted_at` | projects | `deleted_at` | Soft-delete queries |
| `ux_project_versions_num` | project_versions | (`project_id`,`version_number`) | Unique version |
| `ix_scenes_project_version` | scenes | `project_version_id` | List scenes |
| `ux_scenes_version_scene_id` | scenes | (`project_version_id`,`scene_id`) | Unique logical scene |
| `ux_scenes_version_order` | scenes | (`project_version_id`,`order_index`) | Order integrity |
| `ix_narrations_project_version` | narrations | `project_version_id` | |
| `ux_narrations_version_beat` | narrations | (`project_version_id`,`beat_id`) | |
| `ix_narrations_scene_row` | narrations | `scene_row_id` | |
| `ix_subtitles_project_version` | subtitles | `project_version_id` | |
| `ix_subtitles_time` | subtitles | (`project_version_id`,`start_sec`) | Timeline debug |
| `ix_assets_project_version` | assets | `project_version_id` | |
| `ux_assets_version_logical` | assets | (`project_version_id`,`logical_key`) | |
| `ix_videos_project` | videos | `project_id` | |
| `ix_videos_primary` | videos | (`project_id`,`is_primary`) | Current video |
| `ix_render_jobs_status` | render_jobs | `status` | Queue |
| `ix_render_jobs_project` | render_jobs | `project_id` | |
| `ux_render_jobs_idem` | render_jobs | `idempotency_key` | Dedup |
| `ix_job_stages_job` | job_stages | `render_job_id` | |
| `ix_artifact_index_lookup` | artifact_index | (`project_version_id`,`artifact_type`,`status`) | Resume/cache |
| `ix_cache_namespace` | cache_entries | (`namespace`,`last_accessed_at`) | GC |
| `ix_metadata_project` | metadata | `project_id` | Unique already |

### 10.3 Optional FTS (Later)

SQLite FTS5 virtual table on `metadata(title, description, tags_json)` for local project search. Not required for V1 MVP.

---

## 11. Filesystem ↔ Database Mapping

| DB Pointer | Typical File |
|------------|--------------|
| `projects.dsl_path` | `artifacts/vN/presentation.dsl.json` |
| `projects.timeline_path` | `artifacts/vN/timeline.json` |
| `narrations.audio_path` | `artifacts/vN/audio/{beat_id}.wav` |
| `subtitle_files.path` | `export/subtitles.{srt,vtt}` |
| `videos.path` | `export/video.mp4` |
| `videos.thumbnail_path` | `export/thumb.jpg` |
| `artifact_index.path` | `artifacts/vN/{artifact_type}.json` |
| `assets.path` | global pack or `artifacts/vN/assets/...` |

**Rule:** If a DB row says `status=ready` but file missing → mark `invalid` and fail resume with `STORAGE_ARTIFACT_MISSING`.

---

## 12. Project Versioning

### 12.1 Goals

- Allow theme/voice re-runs without losing prior MP4s  
- Support resume and debugging (“which DSL produced this video?”)  
- Enable cache reuse across versions when upstream hashes match  

### 12.2 Version Lifecycle

```
create project
   → create project_versions (v1, status=open)
   → run pipeline writing into artifact_root
   → on successful export: seal version (status=sealed)
   → user changes theme:
        → create v2 (parent=v1, change_reason=theme_change)
        → mark v1 superseded (optional keep sealed)
        → regenerate dirty stages only
```

### 12.3 What Is Versioned

| Versioned | Not necessarily versioned |
|-----------|---------------------------|
| DSL, timeline, audio, subs, videos | Original source upload (shared) |
| Scene/narration index rows | Global themes/languages tables |
| artifact_index rows | app_settings |

### 12.4 Current Pointer

`projects.current_version_id` always points at the active version for UI and new jobs.

### 12.5 Immutability Rule

Once `project_versions.status = sealed`:

- Do not mutate artifact files in that version’s `artifact_root`  
- Fixes create a new version  

---

## 13. Backup Strategy

### 13.1 What to Back Up

1. SQLite database file(s) including WAL if checkpoint needed  
2. `data/projects/**`  
3. Optional: theme packs if customized  

Models (Ollama/Piper) are re-downloadable; may exclude from daily backups.

### 13.2 V1 Local Backup Procedure

| Mode | Procedure |
|------|-----------|
| **Consistent snapshot** | Call SQLite `VACUUM INTO 'backups/explainx-YYYYMMDD.db'` **or** run `PRAGMA wal_checkpoint(FULL);` then copy `explainx.db` |
| **Projects** | Copy `data/projects` to `data/backups/projects-YYYYMMDD/` |
| **Bundled backup** | Zip DB + projects into single archive |

### 13.3 Frequency Guidance

| Backup | Cadence |
|--------|---------|
| Before destructive migrations | Always |
| Automatic | Daily if user enabled |
| Before major version regen | Optional project-level snapshot |

### 13.4 Restore

1. Stop API/worker processes  
2. Replace DB file with backup  
3. Restore `projects/` tree to match DB paths  
4. Run `doctor` integrity check (FK + file existence sample)  
5. Start services  

### 13.5 Project-Level Export Backup

Export package (`MP4 + sidecars + metadata + DSL copy`) is a user-facing backup of **outputs**, not a full resumeable workspace. Full resume needs DB rows + `artifacts/`.

---

## 14. Migration Strategy

### 14.1 Tooling

Use a migration runner (e.g. Alembic, custom SQL migrations, or Flyway-style numbered SQL).

Each migration:

- Has unique `version` id  
- Is idempotent where possible  
- Records row in `schema_migrations`  
- Has forward script; backward optional but recommended for dev  

### 14.2 Rules

1. Prefer additive changes (new columns/tables)  
2. Backfill in batches for large local DBs if needed  
3. Never silently drop user project data  
4. Pair code deploy with migration; app refuses start if schema behind  
5. Keep SQLite and Postgres migration parity via dialect templates  

### 14.3 Example Migration Sequence (Informative)

```
20260711_001_init_core
20260711_002_add_job_stages
20260711_003_add_cache_entries
20260711_004_add_plugins
20260712_001_add_subtitle_files
```

### 14.4 Data Migrations vs Schema Migrations

| Type | Example |
|------|---------|
| Schema | Add `videos.bitrate_kbps` |
| Data | Populate `scenes` from existing DSL files for old projects |

Data migrations must be restart-safe.

---

## 15. Integrity, Concurrency & Transactions

### 15.1 SQLite PRAGMA Recommendations (V1)

| PRAGMA | Value | Why |
|--------|-------|-----|
| `journal_mode` | `WAL` | Readers during write |
| `foreign_keys` | `ON` | Enforce FKs |
| `busy_timeout` | `5000`+ ms | Soft lock waits |
| `synchronous` | `NORMAL` | Balance durability/speed locally |

### 15.2 Transactions

- Creating a project + settings + v1 version = **one transaction**  
- Finalizing a job (stages + video + project status) = **one transaction**  
- File writes should complete before committing “ready” status (store `writing` then flip)

### 15.3 Concurrency Policy

- Default: one running `full_pipeline` job per machine  
- Multiple API reads allowed  
- Multi-worker future: lease jobs via `worker_id` + status conditions  

---

## 16. Security & Privacy Considerations

- No plaintext API keys in DB (none required for core)  
- Project paths jail under storage root  
- Soft-deleted projects retained until GC purge  
- Logs/DB should avoid storing full raw document text; keep in files with user control  
- Backup archives may contain educational content — treat as sensitive user data  

---

## 17. Appendix A: DDL Sketch (Informative)

> Informative only — not application code to execute in this phase. Shows intended shape.

```sql
-- projects (abbreviated)
CREATE TABLE projects (
  project_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_path TEXT,
  source_topic TEXT,
  source_hash TEXT NOT NULL,
  theme_id TEXT NOT NULL REFERENCES themes(theme_id),
  source_language_code TEXT NOT NULL REFERENCES languages(language_code),
  target_language_code TEXT NOT NULL REFERENCES languages(language_code),
  voice_id TEXT,
  difficulty TEXT,
  current_version_id TEXT,
  dsl_path TEXT,
  timeline_path TEXT,
  project_root TEXT NOT NULL,
  estimated_duration_sec REAL,
  actual_duration_sec REAL,
  error_code TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  deleted_at TEXT,
  CHECK (status IN ('draft','queued','running','completed','failed','cancelled','archived')),
  CHECK (source_type IN ('pdf','docx','txt','md','topic'))
);

CREATE TABLE render_jobs (
  render_job_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  project_version_id TEXT REFERENCES project_versions(project_version_id),
  job_type TEXT NOT NULL,
  status TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 100,
  coarse_stage TEXT,
  fine_stage TEXT,
  progress_percent REAL,
  idempotency_key TEXT UNIQUE,
  config_json TEXT,
  input_hash TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  error_code TEXT,
  error_message TEXT,
  checkpoint_json TEXT,
  worker_id TEXT,
  queued_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

---

## 18. Appendix B: Example Rows

### 18.1 Project

| project_id | title | status | theme_id | source_language_code |
|------------|-------|--------|----------|----------------------|
| `3f2a…5566` | Binary Search Explained | `completed` | `notebooklm` | `en` |

### 18.2 Scene

| scene_row_id | scene_id | order_index | visual_mode | duration_resolved_sec |
|--------------|----------|-------------|-------------|------------------------|
| `srow_01` | `scene_trace` | 1 | `algorithm_trace` | 12.4 |

### 18.3 Narration

| beat_id | text (abbrev) | duration_sec | audio_path |
|---------|---------------|--------------|------------|
| `nar_02` | Compare the middle element… | 6.2 | `artifacts/v1/audio/nar_02.wav` |

### 18.4 Render Job

| render_job_id | job_type | status | fine_stage |
|---------------|----------|--------|------------|
| `job_9a…` | `full_pipeline` | `completed` | `rendering_agent` |

---

## Closing Statement

ExplainX V1 persistence is a **hybrid architecture**:

```
SQLite  → relationships, jobs, indexes, status
Files   → DSL, timelines, media, stage JSON
Repos → dialect-safe business logic
```

This preserves offline simplicity today and enables PostgreSQL (and later object storage) tomorrow **without rewriting agents or the Presentation DSL**.

---

*End of DATABASE_DESIGN.md*  
*ExplainX Engineering — Pointers in the Database. Truth in Artifacts. Ports Forever.*
