# Architecture

Scout is a single repository with four layers:

```text
Collectors → Normalization → Scoring/Trust → API + Dashboard + MCP
```

## Live AI layer

On top of the deterministic pipeline, Scout adds an optional live-AI layer that
turns a ranked topic into a real, personalized action plan:

```text
app/services/ai_advisor.py       OpenAI-compatible client + deterministic fallback
app/services/runtime_settings.py env-default + runtime-override settings store
app/api/ai.py                    GET /ai/status, POST /ai/plan (public)
app/api/admin.py                 admin-only Settings API (X-Admin-Key gate)
dashboard/admin.html + admin.js  admin Settings page
scout_mcp/                       MCP server (tools for any LLM) — scout_mcp/README.md
```

The default AI gateway is **OllaBridge Cloud**
(<https://huggingface.co/spaces/ruslanmv/ollabridge>), an OpenAI-compatible
endpoint. The daily dataset pipeline stays deterministic; AI is used only for the
on-demand `/api/v1/ai/plan` call, with automatic fallback to templates. See
[AI_AND_ADMIN.md](AI_AND_ADMIN.md).

## Committers.top refactor

The original `committers.top` pattern is a Go CLI that uses GitHub location queries and presets to identify active developers by country/region. Scout adapts that idea into:

```text
app/collectors/committers_collector.py
app/data/locations.py
legacy/committers_top/
```

The collector is used as a **location developer signal**, not as a surveillance tool. The public output should be aggregated.

## News-and-trends refactor

The news-and-trends project pattern is adapted into:

```text
scripts/generate_snapshot.py
scripts/publish_to_huggingface.py
datasets/snapshots/
dashboard/
.github/workflows/daily_trends.yml
```

This gives Scout a repeatable daily data pipeline and static publishing path.
