from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(tags=["locations"])

@router.get("/locations")
def locations():
    path = Path("app/data/locations.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"locations": ["Rome, Italy", "Milan, Italy", "Worldwide"]}
