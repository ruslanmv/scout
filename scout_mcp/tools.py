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


# --- Learning Navigator tools ----------------------------------------------
# These wrap the deterministic learning pipeline (goal -> skill gap -> resources
# -> ranking -> optimized path). AI only narrates a path evidence produced.

def _learning_request(intent: str, query: str, location: str,
                      current_role: str | None = None,
                      current_skills: list[str] | None = None,
                      hours_per_week: float = 8,
                      max_budget: float | None = None,
                      target_role: str | None = None,
                      target_certification: str | None = None):
    from app.services.learning.schemas import Budget, LearningGoalRequest, SkillRef

    country, city = parse_location(location)
    use_location = country.lower() not in GLOBAL
    return LearningGoalRequest(
        intent=intent,  # type: ignore[arg-type]
        query=query,
        current_role=current_role,
        current_skills=[SkillRef(name=s) for s in (current_skills or [])],
        target_role=target_role,
        target_certification=target_certification,
        country=country if use_location else None,
        city=city if use_location else None,
        use_location=use_location,
        hours_per_week=hours_per_week,
        budget=Budget(maximum=max_budget, free_only=(max_budget == 0)),
    )


def _stage_brief(stage) -> dict[str, Any]:
    primary = stage.resources[0].primary if stage.resources else None
    alt = stage.resources[0].alternative if (stage.resources and stage.resources[0].alternative) else None
    return {
        "stage": stage.stage,
        "title": stage.title,
        "skills": stage.skills,
        "estimated_hours": stage.estimated_hours,
        "primary_resource": ({
            "title": primary.resource.title,
            "provider": primary.resource.provider,
            "url": primary.resource.url,
            "price": primary.resource.price_display(),
            "score": primary.score,
        } if primary else None),
        "free_alternative": (alt.resource.title if alt else None),
        "project": (stage.project.title if stage.project else None),
    }


def resolve_learning_goal(query: str, current_role: str = "", location: str = "Worldwide") -> dict[str, Any]:
    """Refine a vague learning request into a recommended target plus alternatives."""
    from app.services.learning import orchestrator

    req = _learning_request("learn_topic", query, location, current_role=current_role or None)
    resolved = orchestrator.resolve_goal(req)
    return {
        "goal_id": resolved.id,
        "recommended": {"title": resolved.recommended.title,
                        "type": resolved.recommended.type,
                        "reason": resolved.recommended.reason},
        "alternatives": [{"title": a.title, "reason": a.reason} for a in resolved.alternatives],
        "location_effect": resolved.location_effect,
    }


def compare_learning_targets(query: str, location: str = "Worldwide") -> dict[str, Any]:
    """List candidate learning targets for a query so the user can compare routes."""
    from app.services.learning import taxonomy

    ranked = sorted(taxonomy.learning_targets(),
                    key=lambda t: sum(1 for k in t["keywords"] if k in query.lower()),
                    reverse=True)
    return {"query": query,
            "targets": [{"title": t["title"], "type": t["type"],
                         "target_role": t.get("target_role"), "reason": t["reason"]}
                        for t in ranked]}


def evaluate_skill_gap(target_role: str, current_skills: list[str] | None = None,
                       location: str = "Worldwide") -> dict[str, Any]:
    """Compute the skills a learner is missing for a target role, in learning order."""
    from app.services.learning import orchestrator

    req = _learning_request("advance_career", target_role, location,
                            current_skills=current_skills, target_role=target_role)
    resolved = orchestrator.resolve_goal(req)
    gap = orchestrator.evaluate_skill_gap(resolved.recommended, req)
    return {
        "goal": resolved.recommended.title,
        "already_known": [i.name for i in gap.required if i.already_known],
        "missing": [{"name": i.name, "priority": i.priority} for i in gap.required
                    if not i.already_known],
    }


def search_learning_resources(query: str, free_only: bool = False, limit: int = 10) -> dict[str, Any]:
    """Search normalized learning resources (courses, videos, labs) across providers."""
    from app.providers import base as providers
    from app.services.learning import taxonomy
    from app.services.learning.schemas import ResourceQuery

    skill = taxonomy.resolve_skill(query)
    rq = ResourceQuery(text=query, skills=[skill.id] if skill else [],
                       free_only=free_only, limit=limit)
    results = providers.search_all(rq)[:limit]
    return {"query": query, "count": len(results),
            "resources": [{"title": r.title, "provider": r.provider, "url": r.url,
                           "price": r.price_display(),
                           "skills": r.skills_taught,
                           "source": r.provenance.source_type} for r in results]}


def find_certifications(query: str, limit: int = 5) -> dict[str, Any]:
    """Find certifications by name, exam code or issuer, with official domains."""
    from app.services.learning import certifications

    certs = certifications.search_certifications(query, limit)
    return {"query": query,
            "certifications": [{"name": c.name, "issuer": c.issuer, "exam_code": c.exam_code,
                                "official_url": c.official_url,
                                "domains": [{"name": d.name, "weight": d.weight} for d in c.domains]}
                               for c in certs]}


def generate_learning_path(query: str, current_role: str = "", current_skills: list[str] | None = None,
                           location: str = "Worldwide", hours_per_week: float = 8,
                           max_budget: float | None = None, intent: str = "learn_topic") -> dict[str, Any]:
    """Generate a full deterministic learning path (skill-gap -> ranked courses ->
    ordered stages with projects). AI narrates; deterministic logic decides."""
    from app.services.learning import orchestrator

    req = _learning_request(intent, query, location, current_role=current_role or None,
                            current_skills=current_skills, hours_per_week=hours_per_week,
                            max_budget=max_budget, target_role=query if intent == "advance_career" else None)
    resolved = orchestrator.resolve_goal(req)
    path = orchestrator.generate_path(req, resolved_goal_id=resolved.id)
    return {
        "path_id": path.path_id,
        "goal": path.resolved_goal.title,
        "summary": path.rationale.summary,
        "location_effect": path.rationale.location_effect,
        "estimated_weeks": path.duration.estimated_weeks,
        "hours_per_week": path.duration.hours_per_week,
        "confidence": path.rationale.confidence,
        "stages": [_stage_brief(s) for s in path.stages],
        "uncovered_skills": path.uncovered_skills,
        "warnings": path.warnings,
        "source": path.source,
    }


def replan_learning_path(path_id: str, completed_stages: list[int] | None = None) -> dict[str, Any]:
    """Regenerate a path after progress, treating completed stages as known skills."""
    from app.services.learning import orchestrator
    from app.services.learning.schemas import LearningGoalRequest, ProgressEvent

    for stage in (completed_stages or []):
        orchestrator.record_progress(ProgressEvent(path_id=path_id, stage=stage, status="completed"))
    path = orchestrator.replan(path_id, LearningGoalRequest())
    if not path:
        return {"error": f"Path '{path_id}' not found."}
    return {"path_id": path.path_id, "goal": path.resolved_goal.title,
            "estimated_weeks": path.duration.estimated_weeks,
            "stages": [_stage_brief(s) for s in path.stages]}


def record_learning_progress(path_id: str, stage: int, status: str = "completed") -> dict[str, Any]:
    """Record that a learner started, completed or skipped a stage of a path."""
    from app.services.learning import orchestrator
    from app.services.learning.schemas import ProgressEvent

    path = orchestrator.record_progress(
        ProgressEvent(path_id=path_id, stage=stage, status=status))  # type: ignore[arg-type]
    if not path:
        return {"error": f"Path '{path_id}' not found."}
    return {"path_id": path_id, "recorded": {"stage": stage, "status": status},
            "events": len(orchestrator.get_progress(path_id))}


def check_source_health(live: bool = False) -> dict[str, Any]:
    """Health of every external source and API Scout uses — signal sources, the AI
    gateway, course providers, and each recommended course/blueprint URL.

    Returns the cached daily snapshot by default; set ``live=True`` to probe now.
    Includes the overall status plus a ``needs_attention`` list of anything down
    or degraded, so an assistant can report exactly what needs a fix."""
    from app.services import health_monitor

    snap = health_monitor.get_health(live=live)
    attention = [{"name": c["name"], "category": c["category"], "status": c["status"],
                  "detail": c.get("detail", ""), "url": c["url"]}
                 for c in snap.get("checks", []) if c["status"] in ("down", "degraded")]
    return {"overall": snap.get("overall"), "source": snap.get("source"),
            "generated_at": snap.get("generated_at"), "counts": snap.get("counts", {}),
            "needs_attention": attention}


def explain_course_recommendation(query: str, location: str = "Worldwide") -> dict[str, Any]:
    """Explain why the top-ranked resource for a query was recommended (reasons + warnings)."""
    from app.services.learning import course_ranker, orchestrator, taxonomy
    from app.providers import base as providers
    from app.services.learning.schemas import ResourceQuery

    req = _learning_request("learn_topic", query, location)
    resolved = orchestrator.resolve_goal(req)
    gap = orchestrator.evaluate_skill_gap(resolved.recommended, req)
    skill = taxonomy.resolve_skill(query)
    rq = ResourceQuery(text=query, skills=[skill.id] if skill else gap.missing_skill_ids, limit=20)
    ranked = course_ranker.rank(providers.search_all(rq), gap, req, mode="topic")
    if not ranked:
        return {"query": query, "error": "No rankable resources found."}
    top = ranked[0]
    return {"query": query, "resource": top.resource.title, "url": top.resource.url,
            "score": top.score, "reasons": top.reasons, "warnings": top.warnings}
