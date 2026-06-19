# API

Run locally:

```bash
uvicorn app.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

## Examples

```bash
curl http://127.0.0.1:8000/api/v1/trends/global
curl "http://127.0.0.1:8000/api/v1/trends/location?country=Italy&city=Rome"
curl "http://127.0.0.1:8000/api/v1/recommendations?country=Italy&city=Rome&goal=build_portfolio&profile=developer"
curl http://127.0.0.1:8000/api/v1/topics/ai-agents/deep-dive
curl http://127.0.0.1:8000/api/v1/matrix/opportunities
```

## Live AI plan

Generate a real, AI-designed study → build → publish path for a topic:

```bash
curl http://127.0.0.1:8000/api/v1/ai/status
curl -X POST http://127.0.0.1:8000/api/v1/ai/plan \
  -H "Content-Type: application/json" \
  -d '{"topic_id":"ai-agents","country":"Italy","city":"Rome","goal":"build_portfolio","profile":"developer"}'
```

Admin-only settings (gated by `SCOUT_ADMIN_KEY`, sent as `X-Admin-Key`):

```bash
curl http://127.0.0.1:8000/api/v1/admin/settings -H "X-Admin-Key: $SCOUT_ADMIN_KEY"
```

See [docs/AI_AND_ADMIN.md](docs/AI_AND_ADMIN.md) for the full AI engine and admin
Settings reference.
