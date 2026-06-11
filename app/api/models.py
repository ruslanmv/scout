from fastapi import APIRouter
from app.services.llm_provider import provider_status
router = APIRouter(tags=["models"])

@router.get("/models/status")
def models_status():
    return provider_status()
