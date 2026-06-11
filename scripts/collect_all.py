#!/usr/bin/env python
"""Collect public signals and refresh Scout datasets.

This is the daily entrypoint used by GitHub Actions. The first version uses
curated/sample signals plus committers.top-inspired location boosts. Production
collectors can be enabled with API tokens without changing the frontend API.
"""
from __future__ import annotations

import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from scripts.generate_snapshot import build_snapshot


def main():
    result = build_snapshot(write=True)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
