"""Public AI endpoints — the live "best path" generator.

These power the dashboard's AI plan. They are safe to expose without auth: they
return advice, never secrets, and degrade to deterministic plans when AI is off.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import ai_advisor
from app.services.recommender import get_topic

router = APIRouter(tags=["ai"])


class PlanRequest(BaseModel):
    topic_id: str | None = None
    topic: dict | None = None
    country: str = "Worldwide"
    city: str | None = None
    goal: str = "build_portfolio"
    profile: str = "developer"


@router.get("/ai/status")
def ai_status():
    return ai_advisor.ai_status()


@router.post("/ai/plan")
def ai_plan(req: PlanRequest):
    topic = req.topic
    if req.topic_id:
        topic = get_topic(req.topic_id) or topic
    if not topic or not topic.get("name"):
        raise HTTPException(status_code=404, detail="Topic not found. Pass a valid topic_id or topic object.")
    return ai_advisor.generate_plan(topic, req.country, req.city, req.goal, req.profile)
