from fastapi import APIRouter
from app.services.llm_provider import provider_status
from app.services import ai_advisor
router = APIRouter(tags=["models"])

@router.get("/models/status")
def models_status():
    return {**provider_status(), "ai": ai_advisor.ai_status()}
