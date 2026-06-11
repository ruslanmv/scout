#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from scripts.generate_snapshot import build_snapshot

if __name__ == "__main__":
    print(json.dumps(build_snapshot(write=True), indent=2))
