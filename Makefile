.PHONY: install run serve dev test snapshot site export-pages build-pages deploy-pages clean

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
PAGES_BRANCH ?= gh-pages

install:
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(PY) -c "import fastapi, uvicorn, pytest, httpx" || $(PIP) install -r requirements.txt -e ".[dev]"
	$(PY) scripts/generate_snapshot.py

run:
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

serve:
	$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

dev: run

test:
	$(PY) -m pytest

snapshot:
	$(PY) scripts/generate_snapshot.py

# Generate the multi-page Scout site (report sections, topics, docs) into scout/
site:
	$(PY) scripts/build_scout_site.py

export-pages:
	$(PY) scripts/export_for_github_pages.py

build-pages: export-pages

# Traditional GitHub Pages deployment.
# Scout is a project site, so publish the CONTENTS of scout/ at the root of
# gh-pages. Publishing public/scout/ would incorrectly create /scout/scout/.
deploy-pages:
	@if [ -n "$$(git status --porcelain -- scout)" ]; then \
		echo "ERROR: scout/ has uncommitted changes."; \
		echo "Run 'make site', review and commit scout/, then run 'make deploy-pages'."; \
		exit 1; \
	fi
	git subtree push --prefix scout origin $(PAGES_BRANCH)

clean:
	rm -rf public site .pytest_cache
