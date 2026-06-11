from __future__ import annotations

from fastapi import APIRouter, Query
from app.services.recommender import rank_for_location, load_topics, get_topic, get_deep_dive
from app.services.analysis_generator import scout_report, visibility_plan, project_blueprints, next_move
from app.services.dataset_store import latest_batches

router = APIRouter(tags=["frontend"])

@router.get("/ui/bootstrap")
def bootstrap(
    country: str = "Italy",
    city: str | None = "Rome",
    goal: str = "build_portfolio",
    profile: str = "developer",
    limit: int = Query(10, ge=1, le=30),
):
    local_topics = rank_for_location(country, city)
    global_topics = load_topics()
    report = scout_report(local_topics, country, city, goal, profile, limit=limit)
    return {
        "report": report,
        "local_topics": local_topics[:limit],
        "global_topics": global_topics[:limit],
        "options": options(),
        "source_health_url": "/api/v1/sources/health",
        "dataset_url": "/api/v1/datasets/latest",
    }

@router.get("/options")
def options():
    return {
        "goals": [
            {"id": "career", "label": "Get a better career"},
            {"id": "build_portfolio", "label": "Build my portfolio"},
            {"id": "create_agents", "label": "Create agents/tools"},
            {"id": "startup", "label": "Find startup ideas"},
            {"id": "research", "label": "Research what is emerging"},
        ],
        "profiles": [
            {"id": "student", "label": "Student"},
            {"id": "developer", "label": "Developer"},
            {"id": "ai_engineer", "label": "AI engineer"},
            {"id": "founder", "label": "Founder"},
            {"id": "enterprise", "label": "Enterprise leader"},
            {"id": "agent", "label": "Agentic AI system"},
        ],
        "locations": ["Rome, Italy", "Milan, Italy", "Turin, Italy", "San Francisco, United States", "Bengaluru, India", "Worldwide"],
        "depth_modes": ["simple", "advanced"],
    }

@router.get("/topics/{topic_id}/visibility-plan")
def topic_visibility_plan(topic_id: str):
    topic = get_topic(topic_id)
    if not topic:
        return {"error": "topic_not_found"}
    return visibility_plan(topic)

@router.get("/topics/{topic_id}/project-blueprints")
def topic_project_blueprints(topic_id: str):
    topic = get_topic(topic_id)
    if not topic:
        return {"error": "topic_not_found"}
    return {"topic_id": topic_id, "projects": project_blueprints(topic)}

@router.get("/topics/{topic_id}/study-plan")
def topic_study_plan(topic_id: str):
    topic = get_topic(topic_id)
    if not topic:
        return {"error": "topic_not_found"}
    return {"topic_id": topic_id, "study_plan": topic.get("study_plan", []), "starter_actions": topic.get("starter_actions", [])}

@router.get("/topics/{topic_id}/next-move")
def topic_next_move(topic_id: str, goal: str = "build_portfolio", profile: str = "developer"):
    topic = get_topic(topic_id)
    if not topic:
        return {"error": "topic_not_found"}
    return next_move(topic, goal, profile)
