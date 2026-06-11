from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from app.models import SignalBundle
from app.services.scorer import trend_score, actionability_score, matrix_value_score, final_score
from app.services.classifier import classify
from app.services.ml_ranker import rerank_topics

DATASET_PATH = Path("datasets/latest.json")
SAMPLE_PATH = Path("app/data/sample_trends.json")

def load_dataset() -> dict:
    path = DATASET_PATH if DATASET_PATH.exists() else SAMPLE_PATH
    return json.loads(path.read_text(encoding="utf-8"))

def _normalize_topic(raw: dict, rank: int | None = None, country: str | None = None, city: str | None = None) -> dict:
    signals = SignalBundle(**raw.get("signals", {}))
    topic = dict(raw)
    topic["trend_score"] = trend_score(signals)
    topic["actionability_score"] = actionability_score(signals)
    topic["matrix_value_score"] = matrix_value_score(signals)
    topic["score"] = final_score(signals)
    topic["rank"] = rank or raw.get("rank")
    priority, labels = classify(topic)
    topic["priority"] = priority
    topic["labels"] = sorted(set(topic.get("labels", []) + labels))
    topic["location_context"] = {"country": country, "city": city} if country else None
    return topic

def load_topics() -> list[dict]:
    data = load_dataset()
    topics = [_normalize_topic(t, i + 1) for i, t in enumerate(data.get("topics", []))]
    return sorted(topics, key=lambda t: t["score"], reverse=True)

def rank_for_location(country: str, city: str | None = None) -> list[dict]:
    data = load_dataset()
    local_boosts = data.get("local_boosts", {})
    key = f"{country.lower()}:{(city or '').lower()}"
    country_key = country.lower()
    boosts = local_boosts.get(key, local_boosts.get(country_key, {}))
    results = []
    for raw in data.get("topics", []):
        t = _normalize_topic(raw, country=country, city=city)
        boost = boosts.get(t["id"], 0)
        t["score"] = round(min(100, t["score"] + boost), 2)
        results.append(t)
    return sorted(results, key=lambda t: t["score"], reverse=True)

def recommend(country: str, city: str | None, goal: str, profile: str, limit: int = 10, depth: str = "summary") -> list[dict]:
    topics = rank_for_location(country, city)
    goal = goal.lower()
    for t in topics:
        if goal in {"build_portfolio", "portfolio", "startup"}:
            t["score"] = round(min(100, t["score"] + t["signals"].get("project_potential", 0) * 0.04), 2)
        if goal in {"career", "job", "get_job"}:
            t["score"] = round(min(100, t["score"] + t["signals"].get("career_value", 0) * 0.04), 2)
        if goal in {"create_agents", "agent_matrix"}:
            t["score"] = round(min(100, t["score"] + t.get("matrix_value_score", 0) * 0.04), 2)
        # Details are controlled at the endpoint/report layer. Keep full topic
        # objects here so frontend and batch generators can reuse the same data.
    topics = rerank_topics(topics, goal=goal, profile=profile)
    return sorted(topics, key=lambda t: t["score"], reverse=True)[:limit]

def get_topic(topic_id: str) -> dict | None:
    topic_id = topic_id.lower()
    for t in load_topics():
        if t["id"] == topic_id:
            return t
    return None

def get_deep_dive(topic_id: str, country: str, city: str | None, goal: str, profile: str) -> dict | None:
    topic = get_topic(topic_id)
    if not topic:
        return None
    from app.services.analysis_generator import topic_deep_dive
    return topic_deep_dive(topic, country, city, goal, profile)
