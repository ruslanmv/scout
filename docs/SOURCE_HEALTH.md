# Source & API health monitor

Scout depends on external data sources, and recommendations are only trustworthy
if their sources are reachable and the recommended course URLs still resolve.
The health monitor probes everything Scout relies on — **daily** — so
maintainers always know what is healthy and what needs a fix.

## What is monitored

| Category | Targets |
| --- | --- |
| `signal_source` | GitHub API, Hugging Face API |
| `ai_gateway` | OllaBridge AI gateway (`/models`) |
| `course_provider` | Microsoft Learn, Open edX, YouTube Data API* |
| `search_provider` | Tavily*, Brave* |
| `course_url` | Every course URL in the static catalog |
| `certification` | Every official certification blueprint URL |

\* Optional providers are **skipped** (not failed) when their API key is absent.

## Status model

Each target resolves to one status — the probe never raises:

- `up` — reachable (2xx/3xx, or 401/403 which means "reachable, auth required").
- `degraded` — rate-limited (429), a 4xx, or an API base that 404s (path moved).
- `down` — connection error/timeout, 5xx, or a **course/blueprint URL that 404s**
  (the resource is gone — the signal we most want).
- `skipped` — an optional provider with no API key configured.
- `unknown` — config-only mode (no network probe was run).

## API

```text
GET /api/v1/health                     liveness of the Scout service itself
GET /api/v1/health/sources             full snapshot (cached daily; ?live=true probes now)
GET /api/v1/health/sources/summary     overall status + counts + "needs_attention" list
```

`GET /health/sources` returns the cached daily snapshot by default (fast). Pass
`?live=true` to probe every target immediately (bounded, ~8s per target).

The MCP tool `check_source_health(live=false)` exposes the same summary to any
LLM client, including a `needs_attention` list of exactly what is broken.

## Daily job

[`scripts/check_source_health.py`](../scripts/check_source_health.py) probes
every target and writes timestamped snapshots to `datasets/health/`
(`latest.json` + `YYYY-MM-DD.json`) and `public/health.json`. The
[`source_health` workflow](../.github/workflows/source_health.yml) runs it on a
daily cron and commits the snapshot, so the repository always carries an
up-to-date, auditable record of source health.

```bash
python scripts/check_source_health.py            # probe + write snapshot
python scripts/check_source_health.py --public   # also write public/health.json
python scripts/check_source_health.py --fail-on-down   # non-zero exit if any source is down
```

Optional provider keys (`YOUTUBE_API_KEY`, `TAVILY_API_KEY`, `BRAVE_API_KEY`)
enable those targets; without them the providers are reported as `skipped`.

> The monitor is not cosmetic: it already caught several catalog course URLs that
> had gone 404 and drove them to verified, resolving replacements — exactly the
> "keep sources fixed" loop it exists to close.
