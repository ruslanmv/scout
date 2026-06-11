from __future__ import annotations

from fastapi import APIRouter, Query
from app.services.dataset_store import latest_batches
from scripts.generate_snapshot import build_snapshot

router = APIRouter(tags=["batches"])

@router.get("/batches/latest")
def get_latest_batches(limit: int = Query(30, ge=1, le=500)):
    data = latest_batches()
    if "reports" in data:
        data = dict(data)
        data["reports"] = data.get("reports", [])[:limit]
    return data

@router.post("/batches/generate")
def generate_batches():
    # Useful for local/admin usage. In production prefer the scheduled workflow.
    return build_snapshot(write=True)
