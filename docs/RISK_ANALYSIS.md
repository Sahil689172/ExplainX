# ExplainX — Risk Analysis (Engineering Risk Register)

**Document Status:** Canonical Engineering Risk Register  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Owner:** ExplainX Engineering  
**Review Cadence:** At each milestone exit + after production incidents  
**Companions:**  
[`TECH_STACK.md`](./TECH_STACK.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`AGENT_SPECIFICATIONS.md`](./AGENT_SPECIFICATIONS.md) ·  
[`DATABASE_DESIGN.md`](./DATABASE_DESIGN.md) ·  
[`ROADMAP.md`](./ROADMAP.md) ·  
[`DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md)  

> **Purpose:** Identify technical risks before and during implementation, with probability, impact, mitigation, recovery, monitoring, and future improvements.  
> This is a living register — update via PR when risks are accepted, retired, or newly discovered.

---

## Table of Contents

1. [How to Use This Register](#1-how-to-use-this-register)
2. [Risk Rating Model](#2-risk-rating-model)
3. [Risk Heat Summary](#3-risk-heat-summary)
4. [Risk Catalog](#4-risk-catalog)
5. [Cross-Cutting Risk Themes](#5-cross-cutting-risk-themes)
6. [Risk Review Process](#6-risk-review-process)
7. [Appendix: Risk ID Index](#7-appendix-risk-id-index)

---

## 1. How to Use This Register

For every significant design or milestone:

1. Scan risks related to the phase (`ROADMAP.md`)  
2. Confirm mitigations exist in code/docs  
3. Add monitoring hooks if missing  
4. Record residual risk acceptance in ADR if needed  

**Status values:** `Open` · `Mitigated` · `Accepted` · `Retired`

---

## 2. Risk Rating Model

### 2.1 Probability

| Level | Meaning |
|-------|---------|
| **Low** | Unlikely in normal V1 usage |
| **Medium** | Occasional; expected for some users/inputs |
| **High** | Likely without controls |

### 2.2 Impact

| Level | Meaning |
|-------|---------|
| **Low** | Minor UX annoyance; easy workaround |
| **Medium** | Job fails or quality drops; recoverable |
| **High** | Data loss, systemic unreliability, OOM, unusable product |
| **Critical** | Privacy breach, corrupt DB widespread, unrecoverable user work |

### 2.3 Priority Score (Qualitative)

Prioritize **High/Critical impact** and **High probability** first.  
Offline RAM and LLM hallucination risks are treated as first-class.

---

## 3. Risk Heat Summary

| ID | Risk | Prob. | Impact | Priority |
|----|------|-------|--------|----------|
| R01 | Large PDF processing failures/slowness | Medium | Medium | High |
| R02 | Memory exhaustion (16GB) | High | High | Critical |
| R03 | Rendering speed too slow | High | Medium | High |
| R04 | LLM hallucinations / wrong pedagogy | High | High | Critical |
| R05 | Translation quality issues | Medium | Medium | High |
| R06 | Voice quality / intelligibility | Medium | Medium | Medium |
| R07 | Animation complexity / motion sickness | Medium | Medium | Medium |
| R08 | Large projects / long videos | Medium | High | High |
| R09 | Rendering failures (encode/mux) | Medium | High | High |
| R10 | Storage / disk space issues | Medium | High | High |
| R11 | Agent JSON contract drift | Medium | High | High |
| R12 | Timeline–audio desync | Medium | High | High |
| R13 | Asset pack missing / path break | Medium | Medium | Medium |
| R14 | SQLite concurrency / lock errors | Low | Medium | Medium |
| R15 | Model install / version skew | High | Medium | High |
| R16 | Windows native dependency pain (FFmpeg/Ollama) | High | High | High |
| R17 | Scope creep toward generative video | Medium | High | High |
| R18 | Cache invalidation bugs | Medium | Medium | Medium |
| R19 | Subtitle readability / timing | Medium | Low | Low |
| R20 | Privacy leakage via logs/debug | Low | Critical | High |
| R21 | Plugin supply-chain / unstable plugins | Low | High | Medium |
| R22 | Iris Xe encoder unpredictability | Medium | Low | Low |
| R23 | Incomplete resume after crash | Medium | High | High |
| R24 | Frontend/API contract drift | Medium | Medium | Medium |
| R25 | Test environment ≠ user offline machine | High | Medium | High |

---

## 4. Risk Catalog

---

### R01 — Large PDF Processing

| Field | Detail |
|-------|--------|
| **Description** | Large or scanned PDFs cause slow extraction, empty text, high memory, or partial garbage content feeding downstream agents. |
| **Probability** | Medium |
| **Impact** | Medium (failed jobs, poor scripts); High if silent garbage becomes confident wrong video |
| **Mitigation** | Size limits; page batching; extraction warnings; empty-content hard fail; prefer MD/TXT; structure/cleaning heuristics; doctor guidance |
| **Recovery Strategy** | User re-uploads cleaner source; resume from parser after fix; allow topic mode fallback |
| **Monitoring Strategy** | Log page counts, char counts, warning codes (`PARSER_*`); track empty-extract rate |
| **Future Improvements** | OCR plugin; streaming parsers; user preview of extracted text before generate |

**Status:** Open (design mitigations in specs)

---

### R02 — Memory Usage / OOM on 16GB

| Field | Detail |
|-------|--------|
| **Description** | Concurrent LLM + translation + whisper + frame buffers exceed RAM and crash the process. |
| **Probability** | High (without controls) |
| **Impact** | High |
| **Mitigation** | Sequential model load/unload; concurrency=1; 720p draft default; scene-chunked render; avoid simultaneous heavy models; Qwen 3B default |
| **Recovery Strategy** | Restart worker; resume from last checkpoint; retry render-only; prompt user to close other apps |
| **Monitoring Strategy** | Log RSS estimates per stage; doctor free RAM check; job failure code `AGENT_TIMEOUT`/`OOM`-mapped |
| **Future Improvements** | Adaptive quality; memory budgeter; quantized models; process isolation per stage |

**Status:** Open — top priority for Phase 10

---

### R03 — Rendering Speed

| Field | Detail |
|-------|--------|
| **Description** | CPU encode makes multi-minute videos feel “broken” due to long waits without feedback. |
| **Probability** | High |
| **Impact** | Medium (UX/perception); Low if progress is excellent |
| **Mitigation** | Progress events; draft profile; optional QSV; cancel/pause; don’t block HTTP on encode |
| **Recovery Strategy** | Leave timeline intact; re-encode with draft; cloud render later (V4 opt-in) |
| **Monitoring Strategy** | Stage timers; frames/sec metrics; encode duration histograms |
| **Future Improvements** | Hardware encode auto-detect; chunk parallel encode; cloud plugin |

**Status:** Open

---

### R04 — LLM Hallucinations

| Field | Detail |
|-------|--------|
| **Description** | Local LLM invents facts, wrong algorithms, or unsafe educational content; Visual Planner requests generative images or nonsense diagrams. |
| **Probability** | High |
| **Impact** | High (trust, pedagogy) |
| **Mitigation** | Strict JSON schemas; diagram-first visual modes; grounding in extracted knowledge; coverage checks; temperature control; repair loops; refuse image-only plans without plugin; human export disclaimer |
| **Recovery Strategy** | Regenerate from knowledge stage; allow user difficulty/topic constraints; keep artifacts for debug |
| **Monitoring Strategy** | Validation failure rates; empty-concept rate; user regen rate; spot-check golden educational fixtures |
| **Future Improvements** | Citation back to source spans; retrieval over document chunks; optional fact-check agent; UI source preview |

**Status:** Open — critical product risk

---

### R05 — Translation Quality

| Field | Detail |
|-------|--------|
| **Description** | IndicTrans2 mistranslates technical terms, breaks code identifiers, or produces awkward narration for TTS. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | Glossary preserve lists; translate only when languages differ; keep source pack; allow English fallback; limit to supported pairs |
| **Recovery Strategy** | Re-run Translation Agent with glossary; disable translation; regenerate voice from source language |
| **Monitoring Strategy** | Log language pair, char counts, failure rates; optional user rating later |
| **Future Improvements** | Domain glossaries; more models; dual-language subtitles for verification |

**Status:** Open

---

### R06 — Voice Quality

| Field | Detail |
|-------|--------|
| **Description** | Piper voice sounds unnatural, mispronounces terms, or pacing hurts comprehension. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | TTS-friendly script rules; speaking_rate control; curated voice list; SSML-like pauses via punctuation; preview beat audio in UI later |
| **Recovery Strategy** | Switch voice_id; regenerate narration only; adjust rate |
| **Monitoring Strategy** | Synth failure rates; average duration vs estimate; user voice change frequency |
| **Future Improvements** | Better local voices; phoneme hints for glossary terms; emphasis controls |

**Status:** Open

---

### R07 — Animation Complexity

| Field | Detail |
|-------|--------|
| **Description** | Too many concurrent motions, fast zooms, or cluttered scenes reduce educational clarity or cause discomfort. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | Camera limits; animation presets pedagogical-only; object-count warnings; theme motion defaults; validation warnings for overlap |
| **Recovery Strategy** | Re-run Animation/Camera with safer presets; theme `minimal`; reduce scene density via Scene Planner constraints |
| **Monitoring Strategy** | Warning counts (`S004` overcrowding); user regen-with-minimal-theme |
| **Future Improvements** | Motion linter; accessibility “reduce motion” export mode |

**Status:** Open

---

### R08 — Large Projects / Long Videos

| Field | Detail |
|-------|--------|
| **Description** | Long textbooks produce huge scripts, many scenes, large audio sets, and multi-GB artifacts. |
| **Probability** | Medium |
| **Impact** | High (time, disk, memory) |
| **Mitigation** | `max_scenes`; duration targets; chapter-split future; export quality caps; disk checks before render; warn on large source |
| **Recovery Strategy** | Split into multiple projects; resume partial; draft quality; delete temp frames |
| **Monitoring Strategy** | Artifact size bytes; scene counts; estimated duration; disk free |
| **Future Improvements** | Automatic chaptering; multi-part export; progressive streaming preview |

**Status:** Open

---

### R09 — Rendering Failures

| Field | Detail |
|-------|--------|
| **Description** | FFmpeg encode/mux fails (codec, path, permissions, partial MP4), leaving failed jobs. |
| **Probability** | Medium |
| **Impact** | High |
| **Mitigation** | Preflight doctor; render-ready checklist; quality fallback policy; quarantine partial files; retain DSL/timeline |
| **Recovery Strategy** | Retry render-only job; switch to draft/software x264; fix PATH/permissions; re-export |
| **Monitoring Strategy** | Capture stderr excerpts; `RENDER_ENCODE_FAILED` rates; probe output on success |
| **Future Improvements** | Self-contained FFmpeg bundle; automatic encoder matrix retries |

**Status:** Open

---

### R10 — Storage Issues

| Field | Detail |
|-------|--------|
| **Description** | Disk full, path jail escape attempts, corrupt JSON artifacts, or orphaned files vs DB pointers. |
| **Probability** | Medium |
| **Impact** | High |
| **Mitigation** | Disk space checks; path canonicalization jail; write `writing`→`ready` status flip; soft delete; backup guidance |
| **Recovery Strategy** | Free disk; mark artifacts invalid; rebuild index from filesystem scan; restore backup |
| **Monitoring Strategy** | Doctor free_gb; `STORAGE_*` errors; invalid artifact counts |
| **Future Improvements** | Automatic GC policies; integrity `doctor --repair` |

**Status:** Open

---

### R11 — Agent JSON Contract Drift

| Field | Detail |
|-------|--------|
| **Description** | LLM or code changes emit schemas that break downstream stages or caches. |
| **Probability** | Medium |
| **Impact** | High |
| **Mitigation** | Pydantic validation; schema_version; repair retries; contract tests; versioned prompts |
| **Recovery Strategy** | Fail stage; regenerate agent; bump agent_version invalidating cache |
| **Monitoring Strategy** | `AGENT_VALIDATION_FAILED` rate per agent; repair_attempt averages |
| **Future Improvements** | JSON Schema corpus in `docs/schemas`; fuzz LLM outputs in CI with mocks |

**Status:** Open

---

### R12 — Timeline–Audio Desync

| Field | Detail |
|-------|--------|
| **Description** | Animations/subtitles drift from narration because durations missing, estimated poorly, or bind bugs. |
| **Probability** | Medium |
| **Impact** | High (perceived quality) |
| **Mitigation** | Timeline Agent requires measured voice durations when voice enabled; pads; validation; optional whisper align |
| **Recovery Strategy** | Re-run Voice → Subtitle → Timeline → Render only |
| **Monitoring Strategy** | Compare sum(beat durations) vs timeline.duration_sec; subtitle overlap errors |
| **Future Improvements** | Word-level timing; A/V sync QA metric |

**Status:** Open

---

### R13 — Missing Assets / Broken Paths

| Field | Detail |
|-------|--------|
| **Description** | Icon packs not installed; procedural generator missing; theme fonts absent → compile/render fails. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | Asset fallbacks to geometry; doctor asset checks; theme font bundling; status `fallback` |
| **Recovery Strategy** | Install packs; re-run Asset Agent; use `minimal` theme |
| **Monitoring Strategy** | `missing` asset counts; fallback warning rates |
| **Future Improvements** | Subset asset installer; integrity hashes on packs |

**Status:** Open

---

### R14 — SQLite Concurrency / Locks

| Field | Detail |
|-------|--------|
| **Description** | Concurrent writers cause `database is locked` under WAL stress. |
| **Probability** | Low (V1 single job) · Medium if concurrency raised |
| **Impact** | Medium |
| **Mitigation** | WAL; busy_timeout; single heavy job default; short transactions |
| **Recovery Strategy** | Retry transient; restart API; run integrity check |
| **Monitoring Strategy** | Log lock retries; job start conflicts `JOB_ALREADY_RUNNING` |
| **Future Improvements** | Postgres; queue service |

**Status:** Mitigated by policy (monitor if concurrency increases)

---

### R15 — Model Install / Version Skew

| Field | Detail |
|-------|--------|
| **Description** | Users lack Ollama/Piper models or use incompatible tags; “works on my machine” fails elsewhere. |
| **Probability** | High |
| **Impact** | Medium–High |
| **Mitigation** | Doctor readiness; pinned recommended tags in docs/settings; download scripts; clear `MODEL_UNAVAILABLE` |
| **Recovery Strategy** | Run download_models; switch model setting; mock mode for UI-only |
| **Monitoring Strategy** | Doctor check results; job failures by `*_MISSING` codes |
| **Future Improvements** | Installer bundles; model version lockfile |

**Status:** Open

---

### R16 — Windows Native Dependency Pain

| Field | Detail |
|-------|--------|
| **Description** | FFmpeg not on PATH; Ollama service down; antivirus locks files; path length issues. |
| **Probability** | High |
| **Impact** | High |
| **Mitigation** | Doctor; documented install; configurable binary paths; avoid fragile assumptions |
| **Recovery Strategy** | Fix PATH; restart services; move data root shorter path |
| **Monitoring Strategy** | Doctor failures; startup self-test |
| **Future Improvements** | Bundled binaries in installer; health tray app |

**Status:** Open

---

### R17 — Scope Creep Toward Generative Video

| Field | Detail |
|-------|--------|
| **Description** | Pressure to “make it like Sora” undermines presentation-DSL architecture and offline constraints. |
| **Probability** | Medium |
| **Impact** | High (architecture / cost / quality identity) |
| **Mitigation** | Constitution rules; roadmap V3 images as optional plugins only; review checklist architecture rules |
| **Recovery Strategy** | Reject PRs violating A3/A8; ADR required for paradigm changes |
| **Monitoring Strategy** | Architecture review on PRs; plugin flags audit |
| **Future Improvements** | Public positioning docs; demo emphasizing diagram traces |

**Status:** Open (process risk)

---

### R18 — Cache Invalidation Bugs

| Field | Detail |
|-------|--------|
| **Description** | Stale artifacts reused after theme/voice/code version changes → wrong video or subtle bugs. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | Cache keys include config + agent/engine/dsl versions; version seal; tests for theme-only dirty set |
| **Recovery Strategy** | Force full regen; wipe project cache; bump versions |
| **Monitoring Strategy** | Cache hit logs; user “force regenerate” actions |
| **Future Improvements** | Cache explain UI; dependency graph visualizer |

**Status:** Open

---

### R19 — Subtitle Readability / Timing

| Field | Detail |
|-------|--------|
| **Description** | Cues too long, overlap, or poor line breaks hurt accessibility. |
| **Probability** | Medium |
| **Impact** | Low–Medium |
| **Mitigation** | Max chars/lines validation warnings; segmentation rules; burn-in style safe area |
| **Recovery Strategy** | Regenerate subtitles; disable burn-in; edit sidecars later (future) |
| **Monitoring Strategy** | Warning rates on cue length/overlap |
| **Future Improvements** | User subtitle editor; dual-language tracks |

**Status:** Open

---

### R20 — Privacy Leakage via Logs / Debug

| Field | Detail |
|-------|--------|
| **Description** | Full document text logged or debug bundles shared externally. |
| **Probability** | Low (if standards followed) |
| **Impact** | Critical |
| **Mitigation** | Logging standards; hash/count defaults; no cloud telemetry of contents in core; path jail |
| **Recovery Strategy** | Redact logs; rotate; user purge project; incident ADR |
| **Monitoring Strategy** | Code review for log statements; forbid document body logs in CI grep optional |
| **Future Improvements** | Privacy mode switch; automatic log scrubber |

**Status:** Open (controls in standards)

---

### R21 — Plugin Instability / Supply Chain

| Field | Detail |
|-------|--------|
| **Description** | Third-party plugins crash pipeline, phone home, or break DSL. |
| **Probability** | Low in V1 (few plugins) · rising later |
| **Impact** | High |
| **Mitigation** | Core runs with zero plugins; permissions model; offline flag; fail closed to fallbacks |
| **Recovery Strategy** | Disable plugin; rerun core path |
| **Monitoring Strategy** | Plugin error rates; permission grants audit |
| **Future Improvements** | Signed plugins; sandboxing |

**Status:** Accepted residual for V2+ with controls

---

### R22 — Iris Xe Encoder Unpredictability

| Field | Detail |
|-------|--------|
| **Description** | Hardware encode fails or quality poor on some drivers. |
| **Probability** | Medium |
| **Impact** | Low (if CPU fallback works) |
| **Mitigation** | Software x264 default; HW optional; auto-fallback on failure |
| **Recovery Strategy** | Force software profile; update drivers |
| **Monitoring Strategy** | Encoder selected + fallback events |
| **Future Improvements** | Encoder capability matrix tests |

**Status:** Mitigated by default software path

---

### R23 — Incomplete Resume After Crash

| Field | Detail |
|-------|--------|
| **Description** | Process crash mid-stage leaves half-written artifacts and inconsistent DB status. |
| **Probability** | Medium |
| **Impact** | High |
| **Mitigation** | Checkpoint after successful stages; `writing`→`ready` flip; job status reconciliation on startup |
| **Recovery Strategy** | Mark incomplete artifacts invalid; resume from last good checkpoint; restart job |
| **Monitoring Strategy** | Startup reconciliation logs; orphan `writing` artifacts count |
| **Future Improvements** | Transactional outbox; crash tests |

**Status:** Open

---

### R24 — Frontend / API Contract Drift

| Field | Detail |
|-------|--------|
| **Description** | UI assumes fields/endpoints that backend changed, causing silent UX bugs. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | Shared types/OpenAPI; API tests; `API_SPECIFICATION` DoD; versioned `/api/v1` |
| **Recovery Strategy** | Hotfix client/server; feature flag buttons |
| **Monitoring Strategy** | Client error rates; 404/422 spikes |
| **Future Improvements** | Generated client in CI gate |

**Status:** Open

---

### R25 — Test Environment ≠ Offline User Machine

| Field | Detail |
|-------|--------|
| **Description** | CI mocks hide real Ollama/FFmpeg/Windows path issues discovered only by users. |
| **Probability** | High |
| **Impact** | Medium |
| **Mitigation** | Doctor; manual target-hardware checklist; optional nightly real pipeline; document known gaps |
| **Recovery Strategy** | Patch install docs; add doctor checks; hotfix adapters |
| **Monitoring Strategy** | Issue tracker tags `env-windows`; doctor failure telemetry (local only) |
| **Future Improvements** | Windows CI runner with FFmpeg; smoke VM |

**Status:** Open

---

### R26 — Educational Content Liability / Misinformation

| Field | Detail |
|-------|--------|
| **Description** | Generated explainers may be wrong; users may trust them as authoritative curriculum. |
| **Probability** | Medium |
| **Impact** | High (trust/legal perception) |
| **Mitigation** | Product positioning as study aid; validation; grounding; disclaimers in UI/export metadata |
| **Recovery Strategy** | Regen; user correction workflow (future); take down guidance for orgs |
| **Monitoring Strategy** | User reports; fixture curriculum spot checks |
| **Future Improvements** | Source highlights; teacher review mode (V5-ish) |

**Status:** Open (product + tech)

---

### R27 — Long Blocking LLM Calls / Hung Jobs

| Field | Detail |
|-------|--------|
| **Description** | Ollama hangs; job never completes; UI spins forever. |
| **Probability** | Medium |
| **Impact** | Medium |
| **Mitigation** | Timeouts; cancel cooperative; job heartbeat; busy retries bounded |
| **Recovery Strategy** | Cancel job; restart Ollama; resume |
| **Monitoring Strategy** | Stage duration outliers; `AGENT_TIMEOUT` |
| **Future Improvements** | Watchdog worker; automatic model restart |

**Status:** Open

---

## 5. Cross-Cutting Risk Themes

| Theme | Related IDs | Strategic Response |
|-------|-------------|--------------------|
| Resource poverty (RAM/CPU/disk) | R02, R03, R08, R10 | Budgets, draft quality, sequential models |
| Model quality | R04, R05, R06 | Schemas, glossary, diagram-first, disclaimers |
| Pipeline integrity | R11, R12, R18, R23 | Versions, checkpoints, validation |
| Environment/install | R15, R16, R25 | Doctor, pins, docs |
| Architecture identity | R17, R21 | Constitution + review gates |
| Trust & privacy | R20, R26 | Logging rules, positioning |

---

## 6. Risk Review Process

### 6.1 When to Review

- End of each roadmap phase  
- Before tagging a release  
- After any Sev-1/Sev-2 incident (crash, data loss, privacy)  

### 6.2 Review Output

Update this document with:

- Status changes  
- New risks  
- Effectiveness notes on mitigations  
- Links to ADRs/PRs  

### 6.3 Severity Response (Incidents)

| Severity | Example | Response |
|----------|---------|----------|
| Sev-1 | Data loss, privacy leak | Stop release; hotfix; ADR |
| Sev-2 | Widespread render fail | Patch + doctor improvement |
| Sev-3 | Single voice quality complaint | Backlog |

---

## 7. Appendix: Risk ID Index

| ID | Title |
|----|-------|
| R01 | Large PDF processing |
| R02 | Memory usage / OOM |
| R03 | Rendering speed |
| R04 | LLM hallucinations |
| R05 | Translation quality |
| R06 | Voice quality |
| R07 | Animation complexity |
| R08 | Large projects |
| R09 | Rendering failures |
| R10 | Storage issues |
| R11 | Agent JSON contract drift |
| R12 | Timeline–audio desync |
| R13 | Missing assets / paths |
| R14 | SQLite concurrency |
| R15 | Model install / version skew |
| R16 | Windows native dependencies |
| R17 | Generative-video scope creep |
| R18 | Cache invalidation bugs |
| R19 | Subtitle readability |
| R20 | Privacy leakage via logs |
| R21 | Plugin supply-chain |
| R22 | Iris Xe encoder issues |
| R23 | Incomplete resume after crash |
| R24 | Frontend/API contract drift |
| R25 | Test vs real offline machine |
| R26 | Misinformation / liability |
| R27 | Hung LLM / stuck jobs |

---

## Closing Statement

ExplainX’s hardest risks are not “can we call an API?” — they are **RAM**, **local model truthfulness**, **deterministic media integrity**, and **keeping the product a presentation engine**.

Treat this register as part of engineering Definition of Done: if you touch a risky area, leave mitigations and monitoring better than you found them.

---

*End of RISK_ANALYSIS.md*  
*ExplainX Engineering — Name the Risk. Mitigate It. Watch It.*
