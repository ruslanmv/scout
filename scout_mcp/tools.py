"""Scout MCP tool logic (no MCP SDK import, so it stays unit-testable).

Each function wraps Scout's in-process services and returns compact,
LLM-friendly JSON. `server.py` registers these as MCP tools.
"""
from __future__ import annotations

from typing import Any

from app.services import ai_advisor
from app.services.analysis_generator import next_move, project_blueprints
from app.services.matrix_opportunities import matrix_opportunities
from app.services.recommender import (
    get_deep_dive,
    get_topic,
    load_topics,
    rank_for_location,
    recommend,
)

GLOBAL = {"worldwide", "global", "world", "", "anywhere"}


def parse_location(location: str | None) -> tuple[str, str | None]:
    """'Rome, Italy' -> ('Italy', 'Rome'); 'Worldwide' -> ('Worldwide', None)."""
    parts = [p.strip() for p in (location or "Worldwide").split(",") if p.strip()]
    if not parts:
        return "Worldwide", None
    if len(parts) == 1:
        return parts[0], None
    return ", ".join(parts[1:]), parts[0]


def _compact(t: dict) -> dict[str, Any]:
    signals = t.get("signals", {}) or {}
    top = sorted(((k, v) for k, v in signals.items() if v), key=lambda kv: kv[1], reverse=True)[:4]
    return {
        "id": t.get("id"),
        "name": t.get("name"),
        "score": round(float(t.get("score", 0))),
        "priority": t.get("priority"),
        "why_follow": t.get("why_follow") or t.get("summary"),
        "build_idea": (t.get("project_ideas") or [None])[0],
        "skills": (t.get("skills") or [])[:6],
        "top_signals": {k: round(float(v)) for k, v in top},
    }


def _resolve_topic(topic: str) -> dict | None:
    """Resolve a topic by id or fuzzy name match."""
    if not topic:
        return None
    found = get_topic(topic) or get_topic(topic.lower().replace(" ", "-"))
    if found:
        return found
    q = topic.lower().strip()
    for cand in load_topics():
        if q == cand["id"] or q in cand["name"].lower():
            return cand
    return None


def _topics_for(location: str) -> list[dict]:
    country, city = parse_location(location)
    if country.lower() in GLOBAL:
        return load_topics()
    return rank_for_location(country, city)


# --- Tools -----------------------------------------------------------------

def list_hot_trends(location: str = "Worldwide", limit: int = 10) -> dict[str, Any]:
    """Hottest developer & AI technology trends right now, ranked by momentum."""
    topics = _topics_for(location)[: max(1, min(limit, 30))]
    return {"location": location, "count": len(topics), "trends": [_compact(t) for t in topics]}


def recommend_what_to_build(goal: str = "build_portfolio", profile: str = "developer",
                            location: str = "Worldwide", limit: int = 6) -> dict[str, Any]:
    """Rank concrete things to build for a goal/profile, each with a next move."""
    country, city = parse_location(location)
    ranked = recommend(country, city, goal, profile, max(1, min(limit, 20)))
    recs = [{**_compact(t), "next_move": next_move(t, goal, profile)} for t in ranked]
    return {"goal": goal, "profile": profile, "location": location, "recommendations": recs}


def brainstorm_project_ideas(topic: str, count: int = 3) -> dict[str, Any]:
    """Concrete, buildable project blueprints for a topic (title, stack, deliverables)."""
    t = _resolve_topic(topic)
    if not t:
        return {"error": f"Topic '{topic}' not found.",
                "hint": "Call search_trends or list_hot_trends to discover valid topics."}
    return {"topic": t["name"], "topic_id": t["id"],
            "project_blueprints": project_blueprints(t)[: max(1, min(count, 6))]}


def topic_deep_dive(topic: str, location: str = "Worldwide",
                    goal: str = "build_portfolio", profile: str = "developer") -> dict[str, Any]:
    """Full intelligence on one topic: evidence, study plan, projects, risks, opportunities."""
    t = _resolve_topic(topic)
    if not t:
        return {"error": f"Topic '{topic}' not found."}
    country, city = parse_location(location)
    return get_deep_dive(t["id"], country, city, goal, profile)


def find_build_opportunities(location: str = "Worldwide", goal: str = "create_agents",
                             limit: int = 8) -> dict[str, Any]:
    """High-value artifacts to create now (agents, MCP tools, datasets) from current trends."""
    country, city = parse_location(location)
    return matrix_opportunities(country, city, goal, max(1, min(limit, 20)))


def search_trends(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Scout's trend topics by keyword or idea to ground brainstorming in real signals."""
    words = [w for w in (query or "").lower().split() if len(w) > 2]
    scored: list[tuple[int, dict]] = []
    for t in load_topics():
        text = " ".join([t.get("name", ""), t.get("summary", ""), t.get("why_follow", ""),
                         " ".join(t.get("skills", []))]).lower()
        hits = sum(1 for w in words if w in text)
        if (query or "").lower().strip() and (query.lower().strip() in text):
            hits += 2
        if hits:
            scored.append((hits, _compact(t)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return {"query": query, "results": [c for _, c in scored[: max(1, min(limit, 30))]]}


def generate_action_plan(topic: str, goal: str = "build_portfolio", profile: str = "developer",
                         location: str = "Worldwide") -> dict[str, Any]:
    """Live AI 'study -> build -> publish' plan for a topic (OllaBridge Cloud), grounded in real
    signals. Falls back to a deterministic plan if AI is disabled or unreachable."""
    t = _resolve_topic(topic)
    if not t:
        return {"error": f"Topic '{topic}' not found."}
    country, city = parse_location(location)
    return ai_advisor.generate_plan(t, country, city, goal, profile)
