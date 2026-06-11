"""Model-aware ranking utilities for Scout.

This module is intentionally safe by default: it uses deterministic scoring when no
local ML stack is installed, and it can optionally use sentence-transformers or
LLM providers when operators configure them. This keeps the public API reliable
for GitHub Actions, GitHub Pages exports, and local development.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from typing import Iterable

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}")

PROFILE_KEYWORDS = {
    "student": "beginner learning fundamentals portfolio internship projects",
    "beginner": "beginner learning practical projects easy roadmap fundamentals",
    "developer": "developer backend api cloud portfolio github production",
    "ai_engineer": "ai engineer llm rag agents evaluation mlops hugging face",
    "data_scientist": "data analytics machine learning forecasting evaluation dashboards",
    "founder": "startup market opportunity customers prototype product monetization",
    "enterprise": "enterprise governance security compliance reliability integration",
    "researcher": "research papers experiments benchmarks models datasets novelty",
    "agent": "agent matrix mcp reusable tools orchestration automation governance",
}

GOAL_KEYWORDS = {
    "career": "career job demand durable skill employability professional",
    "job": "career job demand durable skill employability professional",
    "get_job": "career job demand durable skill employability professional",
    "build_portfolio": "portfolio project github demo hugging face publish visibility",
    "portfolio": "portfolio project github demo hugging face publish visibility",
    "startup": "startup product market opportunity customers prototype business",
    "research": "research papers benchmark dataset novelty experiment",
    "create_agents": "agent mcp orchestration tools agent-matrix reusable automation",
    "agent_matrix": "agent mcp orchestration tools agent-matrix reusable automation",
}


def _tokens(text: str) -> Counter[str]:
    return Counter(t.lower() for t in TOKEN_RE.findall(text or ""))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _topic_text(topic: dict) -> str:
    parts = [topic.get("name", ""), topic.get("summary", ""), topic.get("why_follow", "")]
    parts += topic.get("starter_actions", []) or []
    parts += topic.get("project_ideas", []) or []
    parts += topic.get("study_plan", []) or []
    parts += topic.get("skills", []) or []
    return " ".join(str(p) for p in parts)


def semantic_fit(topic: dict, goal: str = "career", profile: str = "developer") -> float:
    """Return a 0-100 semantic-fit score.

    If sentence-transformers is available and SCOUT_USE_SENTENCE_TRANSFORMERS=1,
    use a local embedding model. Otherwise use deterministic TF cosine. The
    fallback is intentionally dependency-free and stable in CI.
    """
    query = f"{GOAL_KEYWORDS.get(goal, goal)} {PROFILE_KEYWORDS.get(profile, profile)}"
    text = _topic_text(topic)

    if os.getenv("SCOUT_USE_SENTENCE_TRANSFORMERS") == "1":
        try:
            from sentence_transformers import SentenceTransformer, util  # type: ignore
            model_name = os.getenv("SCOUT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            model = SentenceTransformer(model_name)
            emb = model.encode([query, text], convert_to_tensor=True)
            return round(float(util.cos_sim(emb[0], emb[1]).item()) * 100, 2)
        except Exception:
            pass

    base = _cosine(_tokens(query), _tokens(text)) * 100
    # Add a gentle boost for explicit topic fields that map to public actions.
    signals = topic.get("signals", {}) or {}
    action = 0.30 * signals.get("career_value", 0) + 0.30 * signals.get("project_potential", 0) + 0.20 * signals.get("learning_accessibility", 0) + 0.20 * signals.get("ecosystem_fit", 0)
    return round(min(100.0, 0.55 * base + 0.45 * action), 2)


def rerank_topics(topics: Iterable[dict], goal: str, profile: str) -> list[dict]:
    ranked = []
    for topic in topics:
        item = dict(topic)
        fit = semantic_fit(item, goal=goal, profile=profile)
        item["ml_fit_score"] = fit
        item["score"] = round(min(100.0, 0.82 * float(item.get("score", 0)) + 0.18 * fit), 2)
        ranked.append(item)
    return sorted(ranked, key=lambda t: t.get("score", 0), reverse=True)
