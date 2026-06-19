# Notice

Scout was created as a merged and refactored architecture based on two uploaded project references:

- `committers.top`: used as inspiration for GitHub location presets and top developer activity collection.
- `news-and-trends`: used as inspiration for scheduled collection, JSON snapshots, and static publishing.

The Scout implementation in this package is a new Python/FastAPI-first repository. It includes a lightweight optional Go-compatible preset file under `legacy/committers_top` for reference and migration support.

Live AI plans are generated through the OpenAI-compatible [OllaBridge Cloud](https://github.com/ruslanmv/ollabridge-cloud) gateway by default; it is optional and replaceable (see `docs/AI_AND_ADMIN.md`).
