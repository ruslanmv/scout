from fastapi import APIRouter, HTTPException
from app.services.dataset_store import latest_dataset, dataset_index, snapshot
router = APIRouter(tags=["datasets"])

@router.get("/datasets/latest")
def latest_dataset_endpoint():
    return latest_dataset()

@router.get("/datasets/index")
def dataset_index_endpoint():
    return dataset_index()

@router.get("/datasets/snapshots/{day}")
def dataset_snapshot(day: str):
    data = snapshot(day)
    if data is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return data
