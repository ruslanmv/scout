# Scout — Developer Trend Intelligence

**Scout** is a public, geolocated trend intelligence API and premium dashboard for developers, learners, and agentic AI systems.

It answers one practical question:

> Given a person’s location and goals, what IT topics should they follow, study, build, and publish around now?

Scout combines GitHub developer activity intelligence with automated trend collection and static data publishing in one repository.

Public site target:

```text
https://ruslanmv.com/scout/
```

Local API:

```bash
uvicorn app.main:app --reload
```

## What the frontend consumes

The dashboard is designed to work from one bootstrap endpoint:

```text
GET /api/v1/ui/bootstrap?country=Italy&city=Rome&goal=build_portfolio&profile=developer
```

That returns everything needed for the first screen:

- personalized Scout report,
- local topics,
- global topics,
- project blueprints,
- visibility plan,
- source/dataset URLs,
- UI options.

## Core API endpoints

```text
GET  /api/v1/health
GET  /api/v1/ui/bootstrap
GET  /api/v1/options
GET  /api/v1/report
POST /api/v1/report
GET  /api/v1/recommendations
GET  /api/v1/trends/global
GET  /api/v1/trends/location
GET  /api/v1/topics
GET  /api/v1/topics/{topic_id}
GET  /api/v1/topics/{topic_id}/deep-dive
GET  /api/v1/topics/{topic_id}/study-plan
GET  /api/v1/topics/{topic_id}/project-blueprints
GET  /api/v1/topics/{topic_id}/visibility-plan
GET  /api/v1/topics/{topic_id}/next-move
GET  /api/v1/matrix/opportunities
GET  /api/v1/batches/latest
POST /api/v1/batches/generate
GET  /api/v1/datasets/latest
GET  /api/v1/datasets/index
GET  /api/v1/datasets/snapshots/{day}
GET  /api/v1/search?q=agents
GET  /api/v1/locations
GET  /api/v1/sources/health
GET  /api/v1/models/status
```

## Daily generation workflow

The daily workflow populates frontend-ready datasets and batch reports:

```bash
python scripts/collect_all.py
python scripts/validate_dataset.py
python scripts/export_for_github_pages.py
```

Outputs:

```text
datasets/latest.json
datasets/global/latest.json
datasets/batches/latest.json
datasets/snapshots/YYYY-MM-DD.json
datasets/topics/<topic>/latest.json
datasets/topics/<topic>/evidence.json
datasets/topics/<topic>/deep-dive.json
public/scout/
```

GitHub Actions runs this daily through `.github/workflows/daily_trends.yml`.

## Model strategy

Scout is deterministic by default so the public dataset remains stable, auditable, and cheap to generate.

Optional model hooks are included:

- semantic reranking with `sentence-transformers` when `SCOUT_USE_SENTENCE_TRANSFORMERS=1`,
- optional description enrichment through `SCOUT_ENABLE_LLM=1`,
- provider configuration via `.env.example`.

The fallback model is a reproducible TF/cosine + signal-weighted ranker, so the API works without external credentials.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_snapshot.py
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/dashboard
```

Run tests:

```bash
pytest
```

## Repository role

Scout is the developer-facing form of **Matrix Scout**, the trend-intelligence layer for Agent-Matrix.

It converts public technology signals into:

- recommended topics,
- developer study paths,
- portfolio project ideas,
- visibility/publishing plans,
- Agent-Matrix opportunities,
- MCP tools,
- auditable trend datasets.

## Attribution

This repository includes an adapted design inspired by:

- `ashkulz/committers.top` for GitHub location-based contributor discovery.
- `news-and-trends` style scheduled RSS/data/static publishing workflows.

Scout does not claim ownership of those upstream designs. See `NOTICE.md` and `docs/ARCHITECTURE.md`.
