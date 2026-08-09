# Scout Radar — Global IT Needs Intelligence · Integration Plan

**Status:** proposed · **Approach:** evolve Scout in-place (no separate project) ·
**Target branch for build:** `feat/scout-radar-backend` (draft PR into `master`)

Scout Radar adds a new intelligence layer that answers a different question from
the existing product. Scout today answers *"what should **I** study, build and
publish?"* Radar answers *"what does the **market** need right now, what is
emerging, and what should a product/R&D manager prepare for?"* — as an auditable,
evidence-backed, deterministically-scored feed with AI-written explanations.

This plan is written against the repository as it actually exists today, and
reuses its foundations instead of rebuilding them.

---

## 0. What already exists that we reuse

| Need | Already in the repo | How Radar uses it |
| --- | --- | --- |
| Signal collectors | `app/collectors/{github,huggingface,news,jobs,community,committers}_collector.py` | Wrapped by Radar collectors that emit the universal `Evidence` object. |
| OllaBridge client | `app/services/ai_advisor.py` (`_chat`, `_extract_json`) + `app/services/runtime_settings.py` (`SCOUT_AI_*`, `normalize_base_url`) | `RadarLLMClient` delegates to these — one gateway, one source of truth. |
| Deterministic-core + AI-narration pattern | The Learning Navigator (`app/services/learning/*`) already does exactly "deterministic decides, AI explains, Pydantic validates, deterministic fallback". | Radar follows the same proven split (§2). |
| Dated snapshots | `datasets/snapshots/`, `datasets/index.json` | Extended to `datasets/radar/history/`. |
| Source health | `app/services/health_monitor.py`, `GET /health/sources` | Backs `GET /api/v1/radar/sources/health`. |
| Static export | `scripts/export_for_github_pages.py` copies `scout/` → `public/scout/` | Anything under `scout/radar/` ships automatically. |
| Scheduled automation | `.github/workflows/{daily_trends,source_health}.yml` (`contents: write`, off-round cron, `GITHUB_TOKEN` push) | Template for `scout_radar.yml`. |
| Structured-output validation | Pydantic v2 throughout | The AI extraction/repair loop (§17). |

**Consequence:** Radar is largely *new modules under `app/radar/`* plus a thin set
of wiring changes, not a rewrite. `scripts/collect_all.py` stays a thin wrapper;
we add `scripts/run_radar.py` beside it rather than changing how the daily trend
job is operated.

---

## 1. The one architectural rule: AI and scoring stay separate

The LLM must **never** decide importance. This is the same principle the Learning
Navigator already enforces, applied to market intelligence.

```
Deterministic Python (auditable)          AI (explanatory only)
─────────────────────────────────         ─────────────────────────────
scores, growth, momentum (z-score)        extract needs from evidence
confidence, source diversity              canonicalize similar needs
geographic reach                          summarize evidence
this-week vs last-week deltas             explain "why now"
ranking, horizon assignment               generate research questions
abnormal-acceleration detection           generate manager recommendations
```

Ranking is defensible with numbers; explanations stay useful to humans. The
`publish` node validates every AI object before anything is written to
`datasets/radar/`, so a persuasive-but-wrong model output can never rank #1.

---

## 2. Module layout (`app/radar/`)

```
app/radar/
├── __init__.py
├── config.py            # SCOUT_RADAR_* + SCOUT_LLM_* → reconciled settings (§8)
├── state.py             # RadarState TypedDict (§4)
├── graph.py             # LangGraph StateGraph wiring (§4)
├── collectors/
│   ├── base.py          # EvidenceCollector protocol + registry + safe fan-out
│   ├── github.py        # wraps app/collectors/github_collector.py → Evidence
│   ├── huggingface.py
│   ├── security.py      # NVD/OSV/GHSA feeds
│   ├── research.py      # arXiv/paper feeds
│   ├── jobs.py
│   ├── news.py          # wraps news_collector (RSS)
│   ├── regulation.py    # EU/US regulatory feeds
│   └── community.py
├── nodes/               # one file per LangGraph node
│   ├── collect.py  normalize.py  deduplicate.py
│   ├── extract_needs.py  cluster_needs.py  score_needs.py  forecast.py
│   ├── verify.py  manager_actions.py  publish.py
├── llm/
│   ├── client.py        # RadarLLMClient (delegates to ai_advisor/runtime_settings)
│   ├── prompts.py       # versioned prompt templates, evidence as UNTRUSTED data
│   └── schemas.py       # Pydantic response schemas for each AI call
├── scoring/
│   ├── need_score.py  future_score.py  momentum.py  confidence.py  weighting.py
├── models/
│   ├── evidence.py  need.py  cluster.py  report.py
└── storage/
    ├── repository.py    # read/write datasets/radar/* (atomic, hashed)
    └── history.py       # baseline windows, week-over-week, top movers

scripts/
├── run_radar.py         # compile + invoke radar_graph; --mode daily|weekly|full
├── validate_radar.py    # schema + invariants gate (CI)
└── export_for_github_pages.py   # (existing) already ships scout/radar/
```

Tests mirror this under `tests/radar/` (§21).

---

## 3. Universal `Evidence` object (`models/evidence.py`)

Everything collected becomes one shape first, so scoring never branches on source
type.

```python
class Evidence(BaseModel):
    id: str                       # ev_<ulid>, deterministic from content_hash
    source: str                   # "github" | "nvd" | "arxiv" | "jobs" | ...
    source_family: str            # "adoption" | "security" | "research" | "hiring" | "news" | "regulation"
    source_url: str
    observed_at: str
    title: str
    text: str                     # short extracted evidence, NOT the full page
    technologies: list[str] = []
    regions: list[str] = ["global"]
    industries: list[str] = []
    metrics: dict[str, float] = {}   # stars, growth_7d, cvss, citations, postings…
    source_quality: float = 0.5      # 0..1 prior per source family
    content_hash: str                # dedup key
    license_or_terms: str | None = None
```

Collectors wrap the existing `app/collectors/*` fetchers and map their output into
this model. **We never commit full scraped pages** — only URL, title, date,
metrics, a short extract, hash and source metadata (§11), to keep the git repo
small.

---

## 4. LangGraph state + graph (`state.py`, `graph.py`)

```python
class RadarState(TypedDict, total=False):
    run_id: str; generated_at: str; mode: str; window_days: int
    raw_evidence: list[dict]; normalized_evidence: list[dict]
    need_events: list[dict]; need_clusters: list[dict]
    ranked_needs: list[dict]; future_needs: list[dict]
    manager_actions: list[dict]; research_topics: list[dict]
    source_health: dict; metrics: dict; errors: list[dict]
```

Graph (linear v1, exactly the spec's flow):

```
START → collect → normalize → deduplicate → extract → cluster
      → score → forecast → verify → manager → publish → END
```

- **v1:** linear edges, compiled once in `graph.py`.
- **v2:** `collect` becomes a map/reduce fan-out so GitHub, security, jobs,
  research, etc. run independently (LangGraph Send API), and `extract` batches
  clusters in parallel.
- Every node is pure-ish: reads state slices, returns a partial-state update.
  Nodes **never** fetch arbitrary URLs the model chose, run commands, touch git,
  or read secrets — those stay in Python we control (§18).

---

## 5. AI steps and their contracts (`llm/`)

Each AI call has a strict Pydantic response schema and a deterministic fallback.

| Node | AI produces | Schema (`llm/schemas.py`) | Fallback |
| --- | --- | --- | --- |
| `extract_needs` | `NeedEvent[]` from evidence batches | `NeedEvent` (need, problem, roles, industries, regions, technologies, horizon, evidence_ids) | keyword/tech-cluster heuristic → provisional needs |
| `cluster_needs` | canonical merge of near-duplicate needs | `ClusterDecision` (cluster_id, member_event_ids, canonical_title) | embedding/token-Jaccard clustering (reuse `ml_ranker` style) |
| `manager_actions` | recommendation + research questions per top need | `ManagerBriefing` | template from need + top evidence |
| explanations | `why_now`, `business_need` strings | inline validated | deterministic sentence from metrics |

`extract` vs `cluster` is where the **technology-vs-industry-need** distinction is
made: "MCP is trending" is rejected; "Secure tool authorization for AI agents,
affecting Financial Services / Healthcare" is the target output.

`RadarLLMClient` (`llm/client.py`) is a thin wrapper:

```
RadarLLMClient.complete(messages, schema) →
    reuse ai_advisor._chat(messages, settings)   # OllaBridge /chat/completions
    → ai_advisor._extract_json → schema.model_validate
    → on failure: one repair attempt → deterministic fallback
```

So we get OllaBridge Cloud, OllaBridge-on-Ollama, or deterministic — with no new
HTTP client and no second config surface.

---

## 6. Scoring (`scoring/`, deterministic)

Per-evidence weight, then need score:

```
EvidenceWeight = source_quality × recency × uniqueness
               × regional_relevance × industry_relevance

NeedScore (0..100) =
    0.30·Demand + 0.20·Pain + 0.20·Risk
  + 0.15·Momentum + 0.10·AdoptionGap + 0.05·Confirmation

MomentumZ = (current_7d − baseline_mean) / baseline_std      # baseline = 12 weeks

FutureScore =
    0.25·Acceleration + 0.20·ResearchMomentum + 0.15·HiringMomentum
  + 0.15·Regulation   + 0.15·EmergingAdoption + 0.10·CrossSourceConfirmation
```

Because the two score functions weight different families, a live security
incident won't masquerade as a 2-year strategic bet. `confidence` combines source
diversity, evidence count and cross-family confirmation. All formulas live in
Python and are unit-tested with fixed fixtures.

---

## 7. Horizons & the need card

`horizon ∈ {now (0–4w), emerging (1–6m), next (6–24m)}`, assigned deterministically
from momentum, acceleration and family mix. Each published need:

```json
{ "rank": 1, "id": "agent-security", "title": "Secure AI Agent Authorization",
  "score": 94, "previous_score": 81, "change": 13,
  "momentum": 0.91, "confidence": 0.87, "horizon": "now",
  "evidence_count": 46, "source_count": 7,
  "regions": ["Europe","North America","Asia-Pacific"],
  "why_now": "...", "business_need": "...", "recommended_action": "...",
  "research_questions": ["How can autonomous agents obtain least-privilege access dynamically?"] }
```

---

## 8. Configuration — reconcile, don't fragment

The repo already has two LLM-ish config surfaces: `SCOUT_AI_*` (the live OllaBridge
advisor, in `runtime_settings.py`) and `SCOUT_ENABLE_LLM/SCOUT_LLM_PROVIDER` (the
legacy deterministic-enrichment toggle in `llm_provider.py`). We must not add a
third in isolation.

**Plan:** `app/radar/config.py` reads `SCOUT_RADAR_*` for Radar behaviour and
`SCOUT_LLM_*` for the gateway, but resolves the gateway by **falling back to the
existing `SCOUT_AI_*`** so a single OllaBridge configuration drives everything.

```
SCOUT_RADAR_ENABLED=1
SCOUT_RADAR_WINDOW_DAYS=7
SCOUT_RADAR_BASELINE_DAYS=84
SCOUT_RADAR_MAX_EVIDENCE_PER_SOURCE=500
SCOUT_RADAR_MAX_NEEDS=100
SCOUT_RADAR_AI_EXTRACTION=1
SCOUT_RADAR_AI_EXPLANATIONS=1
SCOUT_RADAR_PUBLISH=1

# Gateway — SCOUT_LLM_* preferred; unset values inherit SCOUT_AI_* (already OllaBridge/free-best)
SCOUT_LLM_PROVIDER=ollabridge        # → runtime_settings ai_provider
SCOUT_LLM_BASE_URL=…                  # → ai_base_url  (default https://ruslanmv-ollabridge.hf.space/v1)
SCOUT_LLM_MODEL=free-best             # → ai_model
SCOUT_LLM_API_KEY=                    # → ai_api_key
SCOUT_LLM_TIMEOUT=60                  # → ai_timeout
```

Documented mapping table ships in `config.py` docstring so operators see one story.

---

## 9. OllaBridge / Ollama execution model

- **GitHub-hosted runners:** use **OllaBridge Cloud** (`free-best`). Do **not**
  download an Ollama model per run.
- **Self-hosted runner (later):** `OllaBridge localhost:11435 → Ollama :11434 →`
  local model, selected purely by `SCOUT_LLM_BASE_URL`.
- **Always:** deterministic fallback so a gateway outage never fails the workflow.

---

## 10. Datasets layout (`datasets/radar/`)

```
datasets/radar/
├── latest.json          # today's ranked needs + now/emerging/next + briefing
├── weekly.json          # Monday deep report (trends, movers, regions)
├── index.json           # manifest of history/needs/regions
├── history/2026-08-09.json …          # dated full snapshots
├── needs/<need_id>.json               # per-need time series
├── regions/<region>.json
└── evidence/latest.json               # compact evidence (no full pages)
```

`storage/repository.py` writes atomically (temp+rename), embeds
`retrieved_at/last_verified_at/content_hash/parser_version`, and dedupes by hash —
same discipline as the learning-resource provenance and the health snapshots.

---

## 11. Historical intelligence (`storage/history.py`)

- Baseline = trailing **12 weeks** of `history/*.json` for momentum z-scores.
- Week-over-week `change` and `previous_score` per need (matched by stable
  `need_id`).
- Top movers, regional deltas, and new/dropped needs for the weekly report.
- Repo-size guard: evidence stores extracts + hashes only; a CI check in
  `validate_radar.py` fails if any radar JSON exceeds a size budget.

---

## 12. API (additive — all existing endpoints untouched)

New router `app/api/radar.py`, mounted at `/api/v1` in `app/main.py`:

```
GET /api/v1/radar                     GET /api/v1/radar/bootstrap        ← primary UI feed
GET /api/v1/radar/needs               GET /api/v1/radar/needs/{id}
GET /api/v1/radar/now|emerging|future
GET /api/v1/radar/regions             GET /api/v1/radar/regions/{region}
GET /api/v1/radar/categories          GET /api/v1/radar/categories/{category}
GET /api/v1/radar/research            GET /api/v1/radar/manager-briefing
GET /api/v1/radar/history             GET /api/v1/radar/history/{need_id}
GET /api/v1/radar/sources/health      ← delegates to health_monitor
```

Endpoints read the published `datasets/radar/*` (fast, static-friendly), exactly
like the current dataset-backed endpoints. `bootstrap` returns everything the
first screen needs in one call, mirroring the existing UI bootstrap pattern.

---

## 13. Website + navigation

Add `scout/radar/` (self-contained page, same design system as `scout/learn/` and
`scout/my-learning/` — Newsreader/Hanken/green, light+dark, live-API-with-cached-
`latest.json`-fallback). `export_for_github_pages.py` already ships anything under
`scout/`, so no export change is required.

Navigation grows to: **Discover · Radar · Learn · Build · Publish**. Add "Radar"
to `scout/scout-landing.{jsx,js}` nav/footer (same two-file edit already used for
Learn and My Learning) and to the learning-page headers.

First screen: a "Needs Now" ranked list, "Fastest rising" + "Next 6–24 months"
panels, a "Why this week" evidence summary, and the manager action + research
question — matching the mock in the brief.

---

## 14. Automation (`.github/workflows/scout_radar.yml`)

Modelled on the existing `source_health.yml`/`daily_trends.yml` (off-round cron
`27 5 * * *`, `contents: write`, `GITHUB_TOKEN` push which safely does **not**
retrigger workflows):

```
daily  : collect → normalize → extract → cluster → score → history → publish latest.json
weekly : daily + 12-week trends, forecasting, movers, regional compare, manager briefing (Monday)
```

Steps: checkout (full history for baselines) → setup-python (pip cache) → install
→ `python scripts/run_radar.py --mode ${{ mode }}` (OllaBridge Cloud env) →
`python scripts/validate_radar.py` → `pytest -q` → export → commit
`datasets/radar public`. `concurrency: scout-radar` prevents overlap.

---

## 15. AI validation & repair loop (`nodes/verify.py`, `llm/client.py`)

```
extract → Pydantic validate → valid ? score : repair(retry 1) → still invalid ? deterministic fallback
```

No malformed AI response ever stops the workflow; the run degrades to deterministic
output and records the failure in `state["errors"]` and the run metrics.

---

## 16. Prompt-injection & autonomy safety

Radar ingests arbitrary internet text, so we assume some is hostile.

- Evidence is passed to the model **inside an explicit untrusted-data envelope**;
  system prompts instruct the model to treat it as data, never instructions.
- The model may **only** return structured objects. It cannot execute commands,
  fetch URLs, touch GitHub, read secrets, write files, or decide publication —
  those are Python-only capabilities in nodes we control.
- `publish` re-validates every object against the schema and size/shape invariants
  before writing. This is the same "AI proposes, deterministic core disposes"
  guarantee already shipping in the Learning Navigator.

---

## 17. Dependencies

Add minimally to `requirements.txt`:

```
langgraph
typing-extensions
```

Optional (add when first needed, not upfront): `httpx`, `tenacity`. **No LangChain**
— LangGraph is used directly as a low-level orchestrator. Keep the existing
`requests`-based OllaBridge client. Pin versions and add an install smoke-test to
CI so a heavy new dep can't silently break the small dependency set.

---

## 18. Testing strategy (`tests/radar/`)

- **Scoring:** fixed evidence fixtures → exact NeedScore/FutureScore/MomentumZ
  (pure functions, no network, no AI).
- **Collectors:** each wrapper maps a canned fetcher payload → valid `Evidence`;
  network calls monkeypatched.
- **Graph:** run `radar_graph` with a fake `RadarLLMClient` (deterministic stub)
  over fixture evidence → assert a well-formed `latest.json` with ranked needs,
  horizons, history deltas.
- **Validation:** `validate_radar.py` invariants (schema, no full pages, size
  budget, stable ids) covered by tests and run in CI.
- **Safety:** an evidence fixture containing an injection string must not change
  control flow; the model stub is never given tool access.
- **API:** `/radar/bootstrap` and friends return the published dataset shape.

Everything runs offline and deterministically, consistent with the current suite.

---

## 19. Milestone 1 — "Scout Radar Backend v1" (the vertical slice to build first)

A complete, trustworthy end-to-end slice before broadening sources:

- LangGraph linear orchestration (`state.py`, `graph.py`, all 10 nodes).
- `RadarLLMClient` over OllaBridge with deterministic fallback.
- **5 real collector families** wrapping existing fetchers: GitHub, Hugging Face,
  news/RSS, jobs, plus one of security/research.
- `Evidence` → `NeedEvent` extraction (AI) → deterministic clustering fallback.
- Deterministic scoring + 12-week history + Now/Emerging/Next ranking.
- Manager recommendations + research questions.
- `datasets/radar/latest.json` + `history/`.
- `GET /api/v1/radar/bootstrap` (+ `now/emerging/future`, `sources/health`).
- `scout/radar/` page + "Radar" in nav.
- `scripts/run_radar.py`, `scripts/validate_radar.py`, `.github/workflows/scout_radar.yml`.
- `tests/radar/` green; docs updated.

### File-by-file task checklist

```
[ ] requirements.txt            + langgraph, typing-extensions
[ ] app/radar/config.py         SCOUT_RADAR_*/SCOUT_LLM_* → runtime_settings bridge
[ ] app/radar/models/*.py       Evidence, NeedEvent, Cluster, Need, RadarReport
[ ] app/radar/collectors/*      base + github, huggingface, news, jobs, security
[ ] app/radar/llm/*             client (reuse ai_advisor), prompts, schemas
[ ] app/radar/scoring/*         weighting, need_score, future_score, momentum, confidence
[ ] app/radar/nodes/*           collect…publish (10 nodes)
[ ] app/radar/storage/*         repository (atomic/hashed), history (baselines)
[ ] app/radar/state.py, graph.py
[ ] scripts/run_radar.py, scripts/validate_radar.py
[ ] app/api/radar.py            + register in app/main.py
[ ] scout/radar/index.html      UI (design-system consistent, cached fallback)
[ ] scout/scout-landing.{jsx,js} nav/footer "Radar"
[ ] .github/workflows/scout_radar.yml
[ ] tests/radar/*               scoring, collectors, graph, validation, api, safety
[ ] datasets/radar/latest.json  first committed snapshot (from a real run)
[ ] docs: this plan + README section + RADAR.md usage
```

### Acceptance criteria (v1 done when)

1. `python scripts/run_radar.py --mode daily` produces a schema-valid
   `datasets/radar/latest.json` with ranked needs, horizons and week-over-week
   deltas — with AI **off** (deterministic) and **on** (OllaBridge).
2. Rankings are reproducible from evidence alone; no AI call changes an order.
3. `GET /api/v1/radar/bootstrap` serves the first screen in one request.
4. `/scout/radar/` renders Now/Emerging/Next with a cached-dataset fallback.
5. A malformed or injected AI response degrades to deterministic output and never
   fails the run or the workflow.
6. `validate_radar.py` blocks oversized or malformed datasets in CI.
7. Existing Scout, Learn and My-Learning features and tests are unaffected.

---

## 20. Milestones 2–4 (after v1 is trustworthy)

- **M2 — Breadth & fan-out:** regulation + community collectors; LangGraph
  map/reduce parallel collection & batched extraction; regions/categories
  endpoints + UI facets.
- **M3 — Weekly executive intelligence:** `weekly.json`, top movers, regional
  comparisons, forecasting, shareable manager briefing; per-need history pages.
- **M4 — Scale & ops:** optional self-hosted runner + local Ollama path; Postgres
  history if git snapshots outgrow the repo; OpenTelemetry run metrics; alerting
  on abnormal acceleration.

---

## 21. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Repo bloat from evidence | Store extracts + hashes only; CI size budget in `validate_radar.py`. |
| Gateway outage on CI | Deterministic fallback everywhere; run never hard-fails on AI. |
| Prompt injection | Untrusted-data envelope; model returns data only; Python holds all capabilities; publish re-validates (§16). |
| Config fragmentation | `SCOUT_LLM_*` inherits `SCOUT_AI_*`; single documented mapping (§8). |
| New heavy dependency (LangGraph) | Pin versions; install smoke-test; no LangChain. |
| Schedule delays / recursive triggers | Off-round cron; `GITHUB_TOKEN` push doesn't retrigger; `concurrency` guard. |
| Scope creep | Ship the v1 vertical slice first; broaden sources only once ranking is trusted. |

---

## 22. Rollout

1. Branch `feat/scout-radar-backend` off latest `master`.
2. Implement Milestone 1 with tests and one real committed `datasets/radar`
   snapshot.
3. Open a **draft PR** into `master`; enable the workflow via `workflow_dispatch`
   first, then the daily schedule once a few manual runs look right.
4. Iterate M2–M4 behind `SCOUT_RADAR_ENABLED` so the layer can ship dark and be
   turned on when the intelligence is trustworthy.

---

### Appendix — end-to-end principle

```
EVIDENCE → NEED EVENTS → NEED CLUSTERS
        → deterministic scoring (WHAT matters) + AI analysis (WHY it matters)
        → SCOUT RADAR → product/R&D manager → BUILD · RESEARCH · PREPARE
```

Numbers you can defend; explanations humans can use. That is the whole point of
keeping AI and scoring separate — and it is the same principle already proven in
Scout's Learning Navigator.
