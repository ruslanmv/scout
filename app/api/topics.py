from fastapi import APIRouter, HTTPException, Query
from app.services.recommender import get_topic, load_topics
router = APIRouter(tags=["topics"])

@router.get("/topics")
def topics(limit: int = Query(50, ge=1, le=200)):
    return {"topics": load_topics()[:limit]}

@router.get("/topics/{topic_id}")
def topic(topic_id: str):
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic
