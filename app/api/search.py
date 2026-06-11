from __future__ import annotations

from fastapi import APIRouter, Query
from app.services.recommender import load_topics
from app.services.ml_ranker import semantic_fit

router = APIRouter(tags=["search"])

@router.get("/search")
def search(q: str, limit: int = Query(10, ge=1, le=50)):
    results = []
    query = q.lower().strip()
    for topic in load_topics():
        text = " ".join([topic.get("name", ""), topic.get("summary", ""), topic.get("why_follow", ""), " ".join(topic.get("skills", []))]).lower()
        lexical = 100 if query in text else 0
        semantic = semantic_fit(topic, goal=query, profile="developer")
        score = max(lexical, semantic)
        if score > 10:
            item = dict(topic)
            item["search_score"] = round(score, 2)
            results.append(item)
    return {"query": q, "results": sorted(results, key=lambda x: x["search_score"], reverse=True)[:limit]}
