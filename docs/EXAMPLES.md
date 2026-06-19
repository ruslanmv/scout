# Examples

```bash
curl /api/v1/trends/global
curl "/api/v1/recommendations?country=Italy&city=Rome&goal=build_portfolio"
curl -X POST /api/v1/ai/plan -H "Content-Type: application/json" \
  -d '{"topic_id":"ai-agents","country":"Italy","city":"Rome","goal":"build_portfolio","profile":"developer"}'
```

Live AI plans and admin settings: [AI_AND_ADMIN.md](AI_AND_ADMIN.md).
