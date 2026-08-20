# Scout 2.0 — Universal Career Radar · Implementation Plan

**Status:** proposed · **Approach:** additive generalization of the existing
codebase (no rewrite) · **Target branch for build:** `feat/scout-2.0`

Scout today answers *"what should a **developer** learn, build, and publish?"*.
Scout 2.0 answers it for **any professional, anywhere, in any language**, while
keeping the core principle unchanged: **deterministic logic decides importance
and order; AI only explains and personalizes.** This plan maps the design
proposal onto the repository as it actually exists so the work is incremental and
each phase ships value on its own.

---

## 0. What already exists that we build on

| Need (proposal) | Already in the repo | Gap to close |
| --- | --- | --- |
| Occupation/skill front door | `GET /api/v1/occupations/search`, `/skills/search`; `app/services/learning/taxonomy.py` (4 tech occupations, skill DAG, empty `external_ids` for esco/onet/case) | Expand taxonomy; back it with ESCO/O*NET; make it the landing input. |
| Course discovery across providers | `app/providers/` (static catalog + Udemy/Coursera/web via Tavily/Brave/DuckDuckGo, per-skill, tagged) | Extend catalog beyond dev topics. |
| Certifications + URL health | `certifications.py`, `app/services/health_monitor.py` (daily probe of every source & course URL) | Add non-tech certification bodies as adapters. |
| Signals | `app/collectors/{github,huggingface,news,jobs,community,committers}_collector.py` | Add a **normalized `Signal`** schema; add **job-postings** and **trends** adapters; keep GitHub/HF as *tech-domain* adapters. |
| Nightly dataset | `scripts/generate_snapshot.py`, `scripts/collect_all.py`, `.github/workflows/daily_trends.yml` (collect → validate → export → commit; dated snapshots) | Add a **NARRATE** stage that pre-computes AI plans into the snapshot. |
| AI plan + fallback | `ai_advisor.generate_plan` (live LLM → deterministic template), `runtime_settings` (OllaBridge, `OB_TOKEN`) | Insert **nightly AI-batch** between live and template in the serving order. |

**Consequence:** most of Scout 2.0 is *new adapters + a taxonomy backbone + one
new pipeline stage*, not a rewrite. The frontend change is the landing input.

---

## 1. Generalize the input (proposal §3)

- **Occupation typeahead.** Replace the closed enum (`scout-data.js` `PROFILES`,
  `scout-landing.jsx` `LField`) with a free-text typeahead calling
  `GET /api/v1/occupations/search`. That endpoint already exists — it becomes the
  front door instead of an internal detail.
- **Domain layer (§3.2).** Group occupations into ~10 domains (ESCO major
  groups). *Shipped as the starter in this change* — `Occupation.domain`, a
  `DOMAINS` registry, and `GET /api/v1/occupations/domains`.
- **Universal intents (§3.3).** Generalize goals to `learn_rising ·
  get_certified · switch_advance · become_visible · find_local_demand`, rendered
  per-domain. The Learning Navigator's four intents already cover most of this;
  add the profession-neutral labels and the **Learn → Practice → Show** output
  framing (superset of study → build → publish).
- **Unknown titles.** Deterministic fuzzy/embedding match to the nearest
  occupation with an *"interpreted as: … — change?"* affordance, so the pipeline
  always has a canonical ID. (`taxonomy.resolve_occupation` already does loose
  matching; add the "interpreted as" surface + an ESCO fallback.)
- **Popular chips.** 8–10 cross-domain chips under the field so the empty box is
  never intimidating.

## 2. Taxonomy backbone — ESCO / O*NET (proposal §3.1, §6.2)

- Load ESCO occupations/skills (27+ languages, free API) as the backbone; join
  O*NET via the ESCO↔O*NET crosswalk. Populate the already-present
  `external_ids.{esco,onet,case}` fields and **key everything — courses, certs,
  jobs, signals, plans — on ESCO URIs** so joins are exact and multilingual.
- Keep the hand-curated Scout skill DAG for emerging roles not yet in ESCO
  (Prompt Engineer, Growth Hacker) — the taxonomy already supports this.
- New adapters live under `app/knowledge/` (`esco.py`, `onet.py`) behind a small
  `OccupationSource` protocol, cached like other sources (§16 of the Navigator
  spec) and health-monitored.

## 3. Pluggable signals (proposal §4)

Define one normalized model and turn every source into an adapter:

```python
class Signal(BaseModel):
    topic_id: str            # ESCO skill URI
    domain: str
    region: str
    source: str
    momentum: float
    demand: float
    evidence: list[dict]
    collected_at: str
```

Adapters (highest ROI first), under `app/collectors/` beside the existing ones:

1. **Job postings — the universal demand signal.** Adzuna (free tier, ~20
   countries), EURES, USAJobs. Extract skills via ESCO dictionary match +
   Pydantic-validated LLM extraction (same trust rule as today).
2. **Search interest** — Google Trends per region/topic.
3. **Course catalogs** — already normalized in `app/providers/`; extend beyond
   dev topics.
4. **Certification bodies** — per-domain registry reusing the certification
   blueprint + URL health monitor.
5. **Domain feeds** — arXiv/PubMed, industry RSS, conference agendas.

GitHub/Hugging Face become *tech-domain* adapters, no longer the core. The daily
health monitor already probes every adapter URL — extend the registry.

## 4. Generalize the output (proposal §5)

- **Opportunity score** stays, computed per (occupation × region) from job demand
  + momentum + a supply proxy (reuse `app/services/scorer.py`).
- **"Show" playbooks per domain** — a deterministic table mapping domain →
  visibility actions (repo/blog · portfolio · CE credits/poster · license entry ·
  client case studies), which AI personalizes. Output template becomes
  **Learn → Practice → Show**.
- **Local radar** is already occupation-agnostic once signals are normalized.

## 5. AI-in-the-dataset — the key change (proposal §6)

Make the **static site intelligent, not templated**, by moving the LLM into the
nightly pipeline. Extend `daily_trends.yml` / `generate_snapshot.py` into:

```
1. COLLECT   all adapters → normalized signals → versioned snapshot (committed)
2. SCORE     deterministic ranking per (domain × region) cell
3. NARRATE   batch LLM pre-generates the plan for the top-N cells
             → snapshot ai_plans/<domain>/<region>/<intent>.json  (source: "ai-batch")
```

- **Serving order** (in `ai_advisor.generate_plan` and `/api/v1/ai/plan`):
  **① live AI** (backend reachable) → **② nightly AI-batch plan from the dataset**
  → **③ deterministic template** (true last resort, labelled via the existing
  `source` field). The static GitHub Pages site now serves **real AI output from
  yesterday's data** — no live backend, no exposed key, bounded cost.
- **Graceful degradation up the taxonomy tree:** an uncovered (occupation × small
  city) cell falls back to the nearest cell (ESCO parent group × country) *before*
  touching templates — not straight to a placeholder.
- **Trust unchanged:** batch outputs use the same Pydantic validate → repair →
  fallback and carry evidence + `last_verified` (§17 of the Navigator spec).
- **Cost control (§6.3):** re-narrate only cells whose deterministic ranking hash
  changed since yesterday; cheap model tier for batch, premium for live.

This directly fixes today's biggest gap — the static site currently serves
deterministic placeholders, not intelligence.

## 6. Phased roadmap (proposal §7)

| Phase | Scope | First concrete files |
| --- | --- | --- |
| **1 — Universal input** | Occupation typeahead + universal intents + **domain layer** (started here); tech stays the signal-rich domain. | `taxonomy.py` domains ✔, `/occupations/domains` ✔, `scout-landing.{jsx,js}`, `scout-data.js` |
| **2 — AI-in-dataset** ✅ *shipped* | Nightly NARRATE stage + serving order ①②③. | `scripts/narrate_batch.py`, `daily_trends.yml`, `ai_advisor.py`, `dashboard/app.js`, `export_for_github_pages.py` |
| **3 — Universal signals** ✅ *shipped (Adzuna)* | Normalized `Signal` schema + Adzuna job-postings adapter across all domains; nightly collect → `datasets/signals/latest.json`; dynamic README consumer. EURES/Trends next. | `app/collectors/signal.py`, `app/collectors/adzuna_collector.py`, `scripts/collect_signals.py`, `daily_trends.yml`, `scripts/update_readme.py` |
| **4 — Localization & breadth** | ESCO multilingual labels + per-domain "Show" playbooks + remaining domains. | `app/knowledge/esco.py`, playbook tables |

**Recommended first build:** Phase 2 (per the proposal) — it makes the existing
product materially better for everyone immediately, with no taxonomy work.

## 7. Risks & mitigations (proposal §8)

| Risk | Mitigation |
| --- | --- |
| Signal sparsity outside tech | Lean on job postings (universal); degrade up the taxonomy tree, never show an empty radar. |
| API terms (LinkedIn/Indeed) | Start with openly licensed sources (Adzuna, EURES, USAJobs, ESCO, O*NET); health monitor flags dead sources. |
| Batch LLM drift/hallucination | Same Pydantic validation + evidence-linking + `last_verified` as live calls today. |
| New-role taxonomy mismatch | Fuzzy/embedding match + "interpreted as" UI keeps the user in control. |
| Cost | Hash-gated re-narration; cheap tier for batch. |

---

## 8. What ships in this change (Phase 1 starter)

A small, safe, tested foundation the rest of Phase 1 builds on:

- `Occupation.domain` field on the schema.
- A `DOMAINS` registry (the ~10 ESCO-major-group domains) in `taxonomy.py`, with
  the existing occupations tagged (`Tech & Data`).
- `taxonomy.list_domains()` and `GET /api/v1/occupations/domains`; occupation
  search results now include `domain`.
- Tests.

## 9. Phase 2 — shipped (AI-in-the-dataset)

The nightly NARRATE stage and the serving order are implemented:

- **`ai_advisor.live_plan`** is now the single LLM entrypoint (narrate or return
  `None`). **`generate_plan`** serves in order **live AI → nightly AI-batch →
  deterministic template**, labelled by the `source` field.
- **`scripts/narrate_batch.py`** pre-computes a plan per (location × goal ×
  profile) cell into `datasets/ai_plans/<key>.json` (`source: "ai-batch"`), with
  a per-cell `content_hash` so only cells whose ranking changed are re-narrated
  (cost control). It is a no-op when AI is disabled/unreachable.
- **`daily_trends.yml`** runs NARRATE after validate; **`export_for_github_pages`**
  ships `datasets/ai_plans/` to `public/data/ai_plans/`.
- **`dashboard/app.js`** serves the batch plan statically when no backend is
  reachable, degrading up the location tree (cell → country → worldwide) before
  hiding. The JS `batchKey` matches the Python slug exactly.

Result: the static GitHub Pages site shows **real AI plans from the latest
dataset** with no live backend and no exposed key — templates are demoted to a
genuine last resort. Trust guarantees are unchanged (same Pydantic
validate/normalize; every plan carries its `source` and `generated_at`).

## 10. Phase 3 — shipped (universal signals, Adzuna)

The demand-signal layer is normalized and cross-domain:

- **`app/collectors/signal.py`** — a single `Signal` schema every adapter emits.
  It ties a `subject` (role/skill/topic) to a `domain` and optional `region`,
  carries comparable `demand` / `momentum` measures in `[0, 1]` plus a raw
  `sample_size`, and keeps verifiable `evidence` URLs. A `key()` gives stable
  identity for idempotent merging across runs.
- **`app/collectors/adzuna_collector.py`** — job-postings adapter over Adzuna's
  open Jobs API. **Fail-safe** (any error → `[]`), **keyless → skip** (no
  `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` → `[]`), and **no fabrication** (demand comes
  from the reported posting `count`; zero-count roles are dropped). Country
  labels map to Adzuna codes, unknown labels degrade to the widest catalog.
- **`scripts/collect_signals.py`** — sweeps every domain × country and writes a
  flat `datasets/signals/latest.json`. Keyless runs still succeed and write a
  valid empty document with a note, so the daily workflow never fails.
- **`daily_trends.yml`** runs the collect step (guarded by repo secrets);
  **`export_for_github_pages`** ships `signals/latest.json` to `public/data/`.

Result: the recommender and the **dynamic README** can read live job-market
demand for *any* profession, degrading cleanly to deterministic ranking when no
source is configured. EURES / USAJobs / Google-Trends adapters slot in behind
the same `Signal` schema with no frontend changes.

Everything else above (Phase 4 localization & breadth) is the roadmap to
implement next on `feat/scout-2.0`.
