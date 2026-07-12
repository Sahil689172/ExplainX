# ADR-0011: Phase 3.9 Quality Assurance Engine

- Status: Accepted
- Date: 2026-07-12

## Context

EducationalScript generation (Phases 3.6–3.8) can still emit scripts that miss
the V1 duration/word band or have empty/weak sections. Downstream scene planning
must not consume unvalidated narration.

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

### Components

| Piece | Role |
|-------|------|
| `QualityInspector` | Collect findings (never invents metrics) |
| `QualityAssuranceService` | Decide PASS / REPAIR; max 2 repair attempts |
| `ScriptRepairService` | Repair **only affected sections** |
| `RepairGenerator` | Protocol |
| `PlaceholderRepairGenerator` / `OllamaRepairGenerator` | Deterministic / LLM repairs |
| `QualityReport` | Structured QA outcome |

### Repair rules

- Never regenerate the full script
- Repair actions: expand, shorten, improve transitions, remove repetition,
  simplify wording, strengthen introduction, improve conclusion
- Recalculate metrics after every repair
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
- Ollama-enabled runs may perform additional per-section repair calls
- Tests: `backend/tests/test_quality_assurance.py`

## Docs

- This ADR
- `docs/ROADMAP.md` Phase 3.9
- Code: `backend/app/features/quality/`
