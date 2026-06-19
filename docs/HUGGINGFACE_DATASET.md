# Hugging Face Dataset

Recommended dataset:

```text
ruslanmv/scout-data
```

Files:

```text
latest.json
global/latest.json
countries/{country}/latest.json
cities/{country}/{city}/latest.json
topics/{topic}/latest.json
topics/{topic}/deep-dive.json
snapshots/YYYY-MM-DD.json
```

The dataset stays deterministic and reproducible; live AI plans are generated separately at request time (see [AI_AND_ADMIN.md](AI_AND_ADMIN.md)).
