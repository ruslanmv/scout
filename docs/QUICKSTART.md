# Get started with Scout

Scout has three entry points: a **browser-based career explorer**, a **local FastAPI server**, and an optional **Model Context Protocol (MCP) server**. You do not need to install Python just to try the browser demo.

## Try it without installing anything

Open the [Scout career explorer](https://ruslanmv.com/scout/) to choose your profession, supported location and objective. The report helps you decide what to learn, practise and publish. You can also explore [Scout Pulse](https://ruslanmv.com/scout/trends/) or the [Learning Navigator](https://ruslanmv.com/scout/learn/).

**About data:** The static site may show curated guidance and illustrative charts when source-attributed hiring observations are unavailable. Check the labels and [methodology](https://ruslanmv.com/scout/dataset/) before treating a ranking as observed demand.

## Local API (Python 3.10+)

From a terminal:

```bash
git clone https://github.com/ruslanmv/scout.git
cd scout
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/generate_snapshot.py
python -m uvicorn app.main:app --reload
```

On Windows PowerShell, use `py -m venv .venv` then `.venv\Scripts\Activate.ps1`; use `python` instead of `python3` if appropriate.

Visit `http://127.0.0.1:8000/docs` for Swagger UI, `http://127.0.0.1:8000/scout/` for Scout, and `http://127.0.0.1:8000/dashboard/` for the dashboard.

Check the API from a **second terminal**:

```bash
curl "http://127.0.0.1:8000/api/v1/ui/bootstrap?country=Italy&city=Rome&goal=build_portfolio&profile=developer"
```

The API is served locally; the static GitHub Pages version does not expose a running FastAPI server.

## Optional MCP server

From the repository root, with your virtual environment active:

```bash
python -m pip install -e ".[mcp]"
python -m scout_mcp
```

This is the documented MCP entry point. Scout does not offer a generic `scout init` wizard or a verified `ruslanmv-scout` PyPI release.

## Contribute and validate

```bash
python -m pip install -e ".[dev]"
python -m pytest
python scripts/export_for_github_pages.py
```

The last command refreshes the static bundle in `public/`; review generated changes rather than committing unrelated data snapshots. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `python: command not found` | Install Python 3.10+ or use `python3` / Windows `py` |
| `ModuleNotFoundError` | Activate your virtual environment and install `requirements.txt` |
| Port 8000 is busy | Run `python -m uvicorn app.main:app --port 8001`, then change the example URL accordingly |
| No job-posting or AI source data | Some integrations need optional credentials. Scout should display curated fallbacks, not claim observed demand |
| Geolocation unavailable | Pick a supported city manually. Browser permission and HTTPS may be required |
| Static links appear outdated | Check GitHub Pages deployment and the `scout/` publishing subtree |

Credentials must be configured through environment variables or your deployment's secret store. **Do not commit API keys, access tokens, or user data.** See [source documentation](DATA_SOURCES.md) and [deployment guidance](GITHUB_PAGES_DEPLOYMENT.md).
