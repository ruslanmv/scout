# Scout datasets

This directory is the local JSON data lake.

- `latest.json`: latest full dataset.
- `global/latest.json`: global trend view.
- `countries/*/latest.json`: country view.
- `cities/*/*/latest.json`: city view.
- `topics/*/deep-dive.json`: topic evidence and recommendations.
- `snapshots/YYYY-MM-DD.json`: historical snapshots.

This data lake is deterministic and reproducible; live AI plans are generated separately at request time (see [../docs/AI_AND_ADMIN.md](../docs/AI_AND_ADMIN.md)).
