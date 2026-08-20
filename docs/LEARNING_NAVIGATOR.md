# Scout Learning Navigator

The Learning Navigator turns *"what should I learn?"* into a concrete, verified,
progress-aware learning path: **topics, courses, certifications, and career
learning paths**.

It extends Scout's existing trend intelligence with four layers:

1. A learner profile and goal model (`LearningGoalRequest`).
2. A skills, occupations, and certifications graph.
3. A verified course-discovery and ranking pipeline.
4. A deterministic, progress-aware learning-path optimizer.

## The most important design decision

The final learning path is **not** generated in one LLM call. A deterministic
pipeline runs first; AI only narrates the result:

```text
understand the user
    → resolve the target        (goal_resolver)
    → calculate the skill gap    (skill_gap)
    → retrieve real resources    (providers)
    → verify and normalize them  (schemas: LearningResource)
    → rank them deterministically (course_ranker)
    → optimize the sequence      (path_optimizer, weighted set-cover)
    → ask AI to explain it        (plan_narrator, optional)
    → validate the output         (validator)
```

AI improves the experience; deterministic logic, evidence, and fallbacks keep
the product reliable. If AI or live search is unavailable, Scout still returns a
useful, honest path from its offline skill graph and static catalog.

## Module map

```text
app/services/learning/
├── schemas.py        # LearningGoalRequest, SkillNode, LearningResource, LearningPath, ...
├── taxonomy.py       # seed skill graph (DAG), occupations, learning targets
├── certifications.py # manually-reviewed certification blueprints (AWS SAA, Azure AI-102)
├── goal_resolver.py  # vague query → recommended target + alternatives
├── skill_gap.py      # required skills, prerequisites, topological order
├── course_ranker.py  # hard filters + transparent mode-specific scoring
├── path_optimizer.py # weighted set-cover + scheduling into stages
├── plan_narrator.py  # optional AI narration (deterministic fallback)
├── validator.py      # rejects unsupported facts and invalid sequences
├── fallback.py       # skill-only path when no resources are usable
└── orchestrator.py   # runs the pipeline; in-process goal/path/progress store

app/providers/
├── base.py           # LearningResourceProvider protocol + registry
├── static_catalog.py # offline, hand-verified free resources (no key needed)
└── web_search.py     # Tavily/Brave discovery for Udemy/Coursera (needs API key)
```

## Intents

`LearningGoalRequest.intent` selects the pipeline mode and ranking weights:

| Intent                    | Example                                   | Ranking weights emphasis        |
| ------------------------- | ----------------------------------------- | ------------------------------- |
| `learn_topic`             | "I want to learn AI"                      | skill coverage, level fit       |
| `prepare_certification`   | "Prepare for AWS SAA"                     | exam-domain coverage, authority |
| `advance_career`          | "Python dev → AI engineer"                | skill-gap coverage, demand      |
| `discover_next`           | "Backend dev — what next?"                | topic + background + demand     |

## API

```text
POST  /api/v1/learning/goals/resolve
POST  /api/v1/learning/resources/search
POST  /api/v1/learning/skill-gap          # known vs missing skills, in learning order
POST  /api/v1/learning/paths
GET   /api/v1/learning/paths/{path_id}
POST  /api/v1/learning/paths/{path_id}/replan
PATCH /api/v1/learning/paths/{path_id}/progress
GET   /api/v1/skills/search
GET   /api/v1/skills/graph                 # nodes/edges for the skill-graph view
GET   /api/v1/occupations/search
GET   /api/v1/certifications/search
GET   /api/v1/providers/health
```

### Resolve a goal

```bash
curl -X POST http://127.0.0.1:8000/api/v1/learning/goals/resolve \
  -H 'Content-Type: application/json' \
  -d '{"query":"I want to learn AI","current_role":"backend developer","country":"Italy","city":"Rome"}'
```

### Generate a path

```bash
curl -X POST http://127.0.0.1:8000/api/v1/learning/paths \
  -H 'Content-Type: application/json' \
  -d '{
    "request": {
      "intent": "advance_career",
      "query": "become an AI engineer",
      "target_role": "AI Engineer",
      "current_skills": [{"name": "Python", "level": "intermediate"}],
      "country": "Italy", "city": "Rome",
      "hours_per_week": 8,
      "budget": {"maximum": 100, "currency": "EUR"}
    }
  }'
```

Path generation runs synchronously and returns a completed plan — it never holds
the request on a live LLM call. AI narration is opt-in via `"use_ai": true` and
always falls back to deterministic text.

## MCP tools

The MCP server (`python -m scout_mcp`) exposes the Navigator to any LLM client:

```text
resolve_learning_goal        compare_learning_targets     evaluate_skill_gap
search_learning_resources    find_certifications          generate_learning_path
replan_learning_path         record_learning_progress     explain_course_recommendation
```

Example:

> Use Scout to create a path for a Python backend developer in Italy who wants
> to move into AI engineering, with a maximum budget of €100.

## User interface

A single-file, self-contained page at **`/scout/learn/`** implements the wizard
and plan view from the product spec, skinned to Scout's existing design system
(Newsreader serif, Hanken Grotesk, green accent, dark constellation panels) with
full light/dark theming.

| Five-step wizard | Generated plan |
| :---: | :---: |
| [![Wizard](assets/screenshots/learn-wizard.png)](assets/screenshots/learn-wizard.png) | [![Plan](assets/screenshots/learn-plan.png)](assets/screenshots/learn-plan.png) |

The [full plan capture](assets/screenshots/learn-plan-full.png) shows the whole
stage timeline, projects, checkpoints, and the evidence & sources table.

- **Five-step wizard:** goal → what you know → where/how → time & budget → review
  target. It resolves the goal live (`/goals/resolve`) and lets the user pick an
  alternative route before generating.
- **Plan view:** goal summary with metrics and the location effect, a known-vs-
  missing **skill-gap map**, a numbered **stage timeline** where every course
  card explains *why it was selected* (reasons, warnings, access, time, level,
  evidence confidence, last-verified date, and a free/cheaper alternative), the
  portfolio project and checkpoint per stage, and an **evidence & sources** list.

The page calls the live API and **falls back to baked-in deterministic demo
data** when the API is unreachable — the same reliability principle as the
backend, and what lets it run as a fully offline prototype.

## Certification prep tracks

Certification goals don't get a flat set-cover of courses — they get a purpose-
built **typed study track** (`app/services/learning/cert_track.py`) that mirrors
how strong candidates actually prepare (spec section 7):

```text
1. Start with the official training      (courses / videos)
2. Build along with real code            (cookbook / quickstarts + a project)
3. Go deep on the reference pillars      (authoritative docs)
4. Study the official exam guide         (blueprint + sample questions)
5. Test yourself with practice questions (practice exam)
6. Join the community                    (partner network / forum)
7. Build 3 real projects                 (portfolio capstone)
8. Register and take the exam            (registration)
```

Phases only appear when Scout has evidence to fill them, so a certification with
only official courses in the catalog produces a shorter, honest track. The seed
catalog ships a complete track for the **Anthropic Claude Certified Architect**
(`cert:claude-architect`) built from real, health-checked Anthropic URLs — exam
codes and prices are never invented (paid items read "Verify on provider").

Career and topic paths gain a **portfolio capstone** stage for the same reason:
a certification proves credibility, a shipped project proves capability.

## Skill-gap & graph (Phase 2)

`POST /learning/skill-gap` resolves a goal and returns the learner's gap — known
skills, missing skills in topological learning order, each with a local-demand-
aware priority — for the UI's skill-gap map. `GET /skills/graph` returns a
`{nodes, edges}` view (edges point prerequisite → dependent, with a `depth` field
for left-to-right layout) for skill-graph visualizations.

## Trust and safety rules (enforced)

- Never claim a certification guarantees employment.
- Never label a course free without a recent, timestamped observation.
- Never invent course titles, ratings, prices, or exam codes — search-discovered
  price/access shows as **"Verify on provider"**.
- Prefer official certification blueprints over third-party summaries.
- Explain *why* location affected a recommendation; location never changes
  technical prerequisites or their order.
- Keep city sharing optional; keep API credentials server-side.
- Preserve source attribution (`provenance`) for every recommendation.

## Course discovery providers

Udemy discontinued its Affiliate API (Jan 2025) and Coursera's catalog needs
partner access, so both are **search-discovery** adapters: Scout finds real,
public course URLs and stores only title/URL/snippet plus provenance, never
inventing ratings, prices or duration (price shows "Verify on provider").

Discovery runs **per missing skill** (`providers.web_discover`), so each found
course is tagged with the one skill it was searched for and the deterministic
ranker can score it. Backends, in priority order:

| Backend | Enable with |
| --- | --- |
| Tavily | `TAVILY_API_KEY` |
| Brave | `BRAVE_API_KEY` |
| DuckDuckGo (keyless, best-effort) | `SCOUT_ENABLE_WEB_DISCOVERY=1` |

With none configured, discovery is a no-op and Scout uses its offline static
catalog — the pipeline still works end to end. When the learner lists a
marketplace (Udemy/Coursera) in `preferred_providers`, a discovered real course
becomes the **primary** recommendation for the skills it covers, with the free
official resource kept as the stage's **alternative**; its warnings
("search-discovered", "verify price") always stand.

The frontend reaches these via the API. Serving the FastAPI backend and the
static site from the same origin (e.g. `uvicorn app.main:app`) wires real data
automatically; a separately hosted backend can be pointed to with
`window.SCOUT_API_BASE`. With no backend reachable, the pages fall back to demo
data (clearly labelled).

## Roadmap

- **Phase 1 (this change):** expanded learner input, seed ESCO/O*NET-ready skill
  graph, Tavily/Brave discovery, static catalog, deterministic ranking and
  ordered paths, source provenance, MCP tools, API.
- **Phase 2:** Credential Engine + Microsoft Learn Platform API, O*NET occupation
  mapping, local skill-gap scoring, certification-prep paths, PostgreSQL + pgvector.
- **Phase 3:** progress tracking at scale, stage assessments, link verification,
  learner feedback, calendar export, Open Badges 3.0 / CLR 2.0.
