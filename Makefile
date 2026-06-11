.PHONY: install run dev test snapshot export-pages build-pages clean

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
install:
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(PY) -c "import fastapi, uvicorn, pytest, httpx" || $(PIP) install -r requirements.txt -e ".[dev]"
	$(PY) scripts/generate_snapshot.py

run:
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev: run

test:
	$(PY) -m pytest

snapshot:
	$(PY) scripts/generate_snapshot.py

export-pages:
	$(PY) scripts/export_for_github_pages.py

build-pages: export-pages

clean:
	rm -rf public site .pytest_cache
