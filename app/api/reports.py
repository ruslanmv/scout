from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.recommender import rank_for_location
from app.services.analysis_generator import scout_report
from app.services.dataset_store import find_report

router = APIRouter(tags=["reports"])

class ReportRequest(BaseModel):
    country: str = "Italy"
    city: str | None = "Rome"
    goal: str = "build_portfolio"
    profile: str = "developer"
    limit: int = 10
    prefer_precomputed: bool = True

@router.get("/report")
def get_report(
    country: str = "Italy",
    city: str | None = "Rome",
    goal: str = "build_portfolio",
    profile: str = "developer",
    limit: int = Query(10, ge=1, le=30),
    prefer_precomputed: bool = True,
):
    if prefer_precomputed:
        cached = find_report(country, city, goal, profile)
        if cached:
            return cached
    topics = rank_for_location(country, city)
    return scout_report(topics, country, city, goal, profile, limit=limit)

@router.post("/report")
def create_report(request: ReportRequest):
    if request.prefer_precomputed:
        cached = find_report(request.country, request.city, request.goal, request.profile)
        if cached:
            return cached
    topics = rank_for_location(request.country, request.city)
    return scout_report(topics, request.country, request.city, request.goal, request.profile, limit=request.limit)
