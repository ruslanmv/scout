"""Batch analysis generation for Scout datasets.

The public frontend should read fast, precomputed report objects. This module
creates those objects daily from normalized topics. Optional LLM providers can be
plugged in later, but deterministic generation is the default so the workflow is
reproducible and trustworthy.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.ml_ranker import rerank_topics

DEFAULT_LOCATIONS = [
    {"country": "Worldwide", "city": None, "slug": "global"},
    {"country": "Italy", "city": "Rome", "slug": "italy/rome"},
    {"country": "Italy", "city": "Milan", "slug": "italy/milan"},
    {"country": "Italy", "city": "Turin", "slug": "italy/turin"},
    {"country": "United States", "city": "San Francisco", "slug": "united-states/san-francisco"},
    {"country": "India", "city": "Bengaluru", "slug": "india/bengaluru"},
]

DEFAULT_GOALS = ["career", "build_portfolio", "create_agents", "startup", "research"]
DEFAULT_PROFILES = ["developer", "ai_engineer", "student", "founder", "enterprise", "agent"]


def confidence_sentence(topic: dict) -> str:
    trust = topic.get("trust", {}) or {}
    label = trust.get("label", "Medium confidence")
    sources = topic.get("sources", []) or []
    names = ", ".join(sorted({s.get("name", "source") for s in sources})[:5]) or "public signals"
    return f"{label}, based on {names}."


def next_move(topic: dict, goal: str, profile: str) -> dict[str, Any]:
    projects = topic.get("project_ideas", []) or [f"Build a practical {topic['name']} demo"]
    study = topic.get("study_plan", []) or [f"Learn the fundamentals of {topic['name']}"]
    if goal in {"build_portfolio", "portfolio"}:
        action = "Build and publish a portfolio project"
    elif goal in {"create_agents", "agent_matrix"}:
        action = "Create a reusable agent or MCP tool"
    elif goal == "startup":
        action = "Validate a product opportunity"
    elif goal == "research":
        action = "Create a benchmark or research note"
    else:
        action = "Study now and build a small proof of work"
    return {
        "action": action,
        "study": study[:3],
        "build": projects[0],
        "publish": ["GitHub repository", "Hugging Face Space", "short technical article"],
        "profile_fit": profile,
    }


def visibility_plan(topic: dict) -> dict[str, Any]:
    slug = topic.get("id", topic.get("name", "topic").lower().replace(" ", "-"))
    skills = topic.get("skills", []) or ["Python", "APIs", "Dashboards", "Documentation"]
    return {
        "github_repo": f"{slug}-demo",
        "huggingface_space": f"{topic.get('name', slug)} Demo",
        "blog_title": f"How I built a {topic.get('name', slug)} project from trend intelligence",
        "skills_to_show": skills[:8],
        "publish_steps": [
            "Create a clean GitHub README with screenshots and architecture.",
            "Publish a working demo or notebook.",
            "Write a short article explaining the problem, approach, and result.",
            "Register the agent/tool in MatrixHub when relevant.",
        ],
    }


def project_blueprints(topic: dict) -> list[dict[str, Any]]:
    ideas = topic.get("project_ideas", []) or []
    if not ideas:
        ideas = [f"{topic['name']} dashboard", f"{topic['name']} API", f"{topic['name']} MCP server"]
    blueprints = []
    for idea in ideas[:3]:
        blueprints.append({
            "title": idea,
            "level": "intermediate",
            "estimated_time": "1-4 weeks",
            "deliverables": ["GitHub repo", "live demo", "short write-up"],
            "stack": (topic.get("skills", []) or ["Python", "FastAPI", "HTML", "JSON"])[:6],
            "why_it_promotes_you": "It creates visible proof that you can convert a trend into a working product artifact.",
        })
    return blueprints


def topic_deep_dive(topic: dict, country: str, city: str | None, goal: str, profile: str) -> dict[str, Any]:
    signals = topic.get("signals", {}) or {}
    return {
        "topic_id": topic["id"],
        "topic_name": topic["name"],
        "location": {"country": country, "city": city},
        "goal": goal,
        "profile": profile,
        "recommendation": topic.get("priority", "monitor_only"),
        "score": topic.get("score", 0),
        "confidence": topic.get("trust", {}),
        "executive_summary": f"{topic['name']} is a strong Scout recommendation because {topic.get('why_follow', topic.get('summary', '')).rstrip('.')}. Your practical move is: {next_move(topic, goal, profile)['build']}.",
        "why_it_matters": topic.get("why_follow") or topic.get("summary"),
        "evidence": {
            "signals": signals,
            "source_summary": confidence_sentence(topic),
            "sources": topic.get("sources", []),
        },
        "local_analysis": {
            "score": signals.get("local_relevance", 0),
            "summary": f"Relevance for {city + ', ' if city else ''}{country} is estimated from local boosts, jobs/community proxies, and topic fit.",
        },
        "global_analysis": {
            "score": topic.get("trend_score", topic.get("score", 0)),
            "summary": "Global momentum combines developer activity, AI ecosystem activity, market/news mentions, job demand, and community signals.",
        },
        "study_plan": topic.get("study_plan", []),
        "project_blueprints": project_blueprints(topic),
        "visibility_plan": visibility_plan(topic),
        "risks": topic.get("risks", ["Signals may be incomplete.", "Some trends can be overhyped."]),
        "agent_matrix_opportunities": [
            {"type": "mcp_server", "name": f"{topic['name']} MCP", "value": "Expose reusable capabilities to agents."},
            {"type": "agent", "name": f"{topic['name']} Scout Agent", "value": "Turn trend intelligence into guided tasks."},
            {"type": "dataset", "name": f"{topic['id']}-signals", "value": "Preserve evidence for reproducible learning."},
        ],
        "raw_data_links": {
            "topic": f"/api/v1/topics/{topic['id']}",
            "deep_dive": f"/api/v1/topics/{topic['id']}/deep-dive",
            "dataset": "/api/v1/datasets/latest",
        },
    }


def scout_report(topics: list[dict], country: str, city: str | None, goal: str, profile: str, limit: int = 10) -> dict[str, Any]:
    ranked = rerank_topics(topics, goal=goal, profile=profile)[:limit]
    top = ranked[0] if ranked else None
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "report_id": f"{country.lower().replace(' ', '-')}-{(city or 'global').lower().replace(' ', '-')}-{goal}-{profile}",
        "generated_at": generated_at,
        "location": {"country": country, "city": city},
        "goal": goal,
        "profile": profile,
        "summary": {
            "headline": "Your next developer advantage is ready." if top else "No report available.",
            "top_topic": top.get("name") if top else None,
            "top_topic_id": top.get("id") if top else None,
            "top_project": (top.get("project_ideas", []) or [None])[0] if top else None,
            "confidence": top.get("trust", {}) if top else {},
            "next_move": next_move(top, goal, profile) if top else {},
        },
        "recommendations": ranked,
        "top_three": ranked[:3],
        "projects": [bp for t in ranked[:5] for bp in project_blueprints(t)[:1]],
        "visibility_plan": visibility_plan(top) if top else {},
        "methodology": {
            "ranking": "trend_score + actionability_score + matrix_value_score + optional semantic fit",
            "model_policy": "Deterministic by default; optional local/hosted model enrichment can be enabled in production.",
        },
    }


def batch_reports(topics_by_location: dict[str, list[dict]], goals: list[str] | None = None, profiles: list[str] | None = None) -> dict[str, Any]:
    goals = goals or DEFAULT_GOALS
    profiles = profiles or DEFAULT_PROFILES
    batches: list[dict[str, Any]] = []
    for loc in DEFAULT_LOCATIONS:
        country, city, slug = loc["country"], loc["city"], loc["slug"]
        topics = topics_by_location.get(slug) or topics_by_location.get("global") or []
        for goal in goals:
            for profile in profiles:
                batches.append(scout_report(topics, country, city, goal, profile, limit=10))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "batch_count": len(batches),
        "goals": goals,
        "profiles": profiles,
        "reports": batches,
    }
