#!/usr/bin/env python

import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import json
from pathlib import Path

data = json.loads(Path("datasets/latest.json").read_text(encoding="utf-8"))
assert "topics" in data and isinstance(data["topics"], list)
for topic in data["topics"]:
    assert "id" in topic and "name" in topic and "signals" in topic
print("Dataset is valid")
