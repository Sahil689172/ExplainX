# ADR-0011: Phase 3.9 Quality Assurance Engine

- Status: Accepted
- Date: 2026-07-12
- Updated: 2026-07-12 (MVP relaxed validation)

## Context

EducationalScript generation (Phases 3.6–3.8) can still emit scripts that are
too short overall, empty, or missing sections. Downstream scene planning must
not consume unvalidated narration. For MVP we prioritize a **stable end-to-end
pipeline** over strict 2–3 minute duration accuracy.

## Decision

Insert a **Quality Assurance** gate after metrics enrichment:

```
TeachingOutline
  → Section Generation
  → EducationalScript
  → ScriptMetricsCalculator
  → QualityAssuranceService
  → Approved EducationalScript (status=ready)
```

### MVP global script validation

Hard-fail only when:

- Estimated duration &lt; 60s or &gt; 300s (configurable via
  `EXPLAINX_SCRIPT_MIN_DURATION_SEC` / `EXPLAINX_SCRIPT_MAX_DURATION_SEC`)
- No teaching sections
- Empty narration on any section
- Duplicate section IDs

**Not** hard-fail:

- Per-section `target_words` drift (guidance for prompts only)
- Total word count outside the old 300–450 band (reported in metrics only)

### Components

| Piece | Role |
|-------|------|
| `QualityInspector` | Collect findings (never invents metrics) |
| `QualityAssuranceService` | Decide PASS / REPAIR; max 2 repair attempts |
| `ScriptRepairService` | Repair **only affected sections** |
| `RepairGenerator` | Protocol |
| `PlaceholderRepairGenerator` / `OllamaRepairGenerator` | Deterministic / LLM repairs |
| `QualityReport` | Structured QA outcome |

### Repair rules (MVP)

Trigger repair **only** for:

- Total duration &lt; 60 seconds (`TOO_SHORT` → expand shortest sections)
- Empty sections (`EMPTY_SECTION`)
- Missing sections (structural; missing outline sections are unrecoverable)

Do **not** repair solely because a section is longer/shorter than `target_words`.
Do **not** repair solely because total duration exceeds the max (reject instead).

Other rules:

- Never regenerate the full script
- Recalculate metrics after every repair (reporting: total words, duration,
  average words per section)
- Revalidate with `ScriptValidator`
- Maximum **2** repair attempts
- If still invalid → `SCRIPT_QUALITY_FAILED` with structured details

### Persistence

```
artifacts/quality_report.json
artifacts/approved_script.json
artifacts/repair_log.json
```

`educational_script.json` continues to store the approved script for existing consumers.

### Non-goals

- No Scene Planning
- No API route changes
- No EducationalScript schema changes

## Consequences

- Generated scripts are only returned when QA approves (`status=ready`)
- MVP accepts a wider duration band so the pipeline completes more reliably
- Ollama-enabled runs may perform additional per-section repair calls
- Tests: `backend/tests/test_quality_assurance.py`

## Docs

- This ADR
- `docs/ROADMAP.md` Phase 3.9
- Code: `backend/app/features/quality/`
