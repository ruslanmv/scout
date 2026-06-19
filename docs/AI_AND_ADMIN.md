# AI Engine & Admin Settings

Scout designs each user's **study → build → publish** path with a real, live AI
call instead of a hardcoded template. The AI is provided by an OpenAI-compatible
gateway — **[OllaBridge Cloud](https://github.com/ruslanmv/ollabridge-cloud)** by
default — and is configurable at runtime from an admin-only Settings page.

## How it works

```text
Dashboard report loads
        │
        ▼
POST /api/v1/ai/plan  ──►  ai_advisor.generate_plan()
        │                        │
        │                        ├─ AI enabled?  ──►  POST {gateway}/v1/chat/completions
        │                        │                    (top topic + its REAL signals)
        │                        │                          │
        │                        │                    parse JSON plan
        │                        │                          │
        │                        └─ on any failure ─►  deterministic template plan
        ▼
Rendered as the "✨ AI plan" card (or the built-in plan)
```

The request sends the top-ranked topic **and the real signals Scout collected**
(GitHub, Hugging Face, news, jobs, community) so the plan is grounded in evidence,
not invented. The `source` field on the response tells you which engine produced
it: `ollabridge-cloud` (live AI) or `deterministic` (built-in fallback).

Scout is **fail-safe**: if AI is disabled, unconfigured, or the gateway is
unreachable, every plan falls back to the deterministic TF/cosine +
signal-weighted templates. The product and the daily dataset never break.

> The **daily public dataset stays deterministic** and auditable. AI only powers
> the live, on-demand `/api/v1/ai/plan` endpoint, so reproducibility is preserved.

## Configuration (environment variables)

Defaults work out of the box against the public gateway with no API key.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCOUT_AI_ENABLED` | `1` | Turn the live AI on/off (`0` = always use built-in plans) |
| `SCOUT_AI_PROVIDER` | `OllaBridge Cloud` | Display label shown in the UI |
| `SCOUT_AI_BASE_URL` | `https://ruslanmv-ollabridge.hf.space/v1` | OpenAI-compatible gateway endpoint |
| `SCOUT_AI_MODEL` | `free-best` | Model/alias to use |
| `SCOUT_AI_API_KEY` | _(empty)_ | Bearer token; blank for the public gateway |
| `SCOUT_AI_TEMPERATURE` | `0.4` | Sampling temperature |
| `SCOUT_AI_TIMEOUT` | `45` | Per-request timeout (seconds) |
| `SCOUT_AI_MAX_TOKENS` | `900` | Max tokens per plan |
| `SCOUT_ADMIN_KEY` | _(unset)_ | Secret that unlocks the admin Settings page. **Unset = admin locked.** |
| `SCOUT_RUNTIME_CONFIG` | `runtime/settings.json` | Where runtime admin overrides are persisted (gitignored) |

### Default gateway

The default points at the Space
<https://huggingface.co/spaces/ruslanmv/ollabridge>. Its API is served from the
direct app subdomain (`ruslanmv-ollabridge.hf.space`), which is what handles
`/v1/chat/completions`.

**URL auto-resolution:** you may set `SCOUT_AI_BASE_URL` (or the admin field) to
either form — Scout normalizes them automatically:

```text
https://huggingface.co/spaces/ruslanmv/ollabridge  ->  https://ruslanmv-ollabridge.hf.space/v1
https://ruslanmv-ollabridge.hf.space               ->  https://ruslanmv-ollabridge.hf.space/v1
```

### Models

The default gateway exposes routing aliases and concrete models, e.g.
`free-best`, `free-fast`, `qwen2.5:1.5b`, `fable-5`, `claude-best`, `gpt-best`.
List them live with `GET {SCOUT_AI_BASE_URL}/models`.

## Admin Settings page

A non-technical admin can configure everything from the browser — no redeploy.

```text
http://127.0.0.1:8000/dashboard/admin.html
```

1. Set the gate (any secret of your choice) and restart Scout:
   ```bash
   export SCOUT_ADMIN_KEY="choose-a-strong-secret"
   ```
2. Open the page and unlock it with that key.
3. Change the provider, model, gateway URL, or paste an API key; toggle AI on/off.
4. Click **Test connection** for a live round-trip check.
5. **Save** — new plans use the values immediately. **Reset** reverts to the
   environment defaults.

If `SCOUT_ADMIN_KEY` is unset the page shows a "locked" notice and the admin API
returns `503` — the safe default for public deployments.

### Security

- The API key is stored server-side and **never returned to the browser** — the
  admin API exposes only `ai_api_key_set` and a masked hint (last 4 chars).
- The admin gate (`SCOUT_ADMIN_KEY`) is **env-only**; it cannot be changed from
  the UI, so the UI can never lock you out or rotate its own gate.
- Runtime overrides live in `runtime/settings.json`, which is gitignored.
- Auth is a shared admin key sent as the `X-Admin-Key` header, compared with a
  constant-time check.

## Endpoints

### Public

```text
GET  /api/v1/ai/status      # is AI on, which provider/model/endpoint
POST /api/v1/ai/plan        # generate a live plan for a topic
```

`POST /api/v1/ai/plan` body:

```json
{
  "topic_id": "ai-agents",
  "country": "Italy",
  "city": "Rome",
  "goal": "build_portfolio",
  "profile": "developer"
}
```

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/ai/plan \
  -H "Content-Type: application/json" \
  -d '{"topic_id":"ai-agents","country":"Italy","city":"Rome","goal":"build_portfolio","profile":"developer"}'
```

Response shape:

```json
{
  "topic_id": "ai-agents",
  "topic_name": "AI Agents and Agentic Workflows",
  "source": "ollabridge-cloud",
  "provider": "OllaBridge Cloud",
  "model": "free-best",
  "generated_at": "2026-06-19T07:09:22Z",
  "headline": "…",
  "why_now": "…",
  "study": ["…"],
  "build": { "title": "…", "description": "…", "stack": ["…"], "deliverables": ["…"] },
  "publish": ["…"],
  "skills": ["…"],
  "risks": ["…"],
  "confidence": "…"
}
```

When AI is off or unavailable the same shape is returned with
`"source": "deterministic"` and a `"note"` explaining why.

### Admin (require `X-Admin-Key`)

```text
GET  /api/v1/admin/enabled    # unauthenticated: is the admin area configured?
GET  /api/v1/admin/settings   # current settings (key masked) + status + defaults
POST /api/v1/admin/settings   # update settings (omit ai_api_key to keep it)
POST /api/v1/admin/test       # live connection test (optionally against proposed values)
POST /api/v1/admin/reset      # clear runtime overrides, revert to env defaults
```

Example:

```bash
curl -s http://127.0.0.1:8000/api/v1/admin/settings -H "X-Admin-Key: $SCOUT_ADMIN_KEY"
```
