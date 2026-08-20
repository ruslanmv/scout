"""Real AI path generation via an OpenAI-compatible gateway (OllaBridge Cloud).

This is the difference between Scout *describing* a trend and Scout *coaching*
you through it. Given a topic and the user's location/goal/profile, the advisor
asks a live language model to design a concrete "study -> build -> publish"
path, grounded in the real signals Scout collected from the internet.

It is deliberately fail-safe: if AI is disabled, unconfigured, or the gateway is
unreachable, every function falls back to Scout's deterministic templates so the
product never breaks. The contract returned to the frontend is identical either
way — only the ``source`` field tells you which engine produced it.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.services import runtime_settings

# Where the nightly NARRATE stage stores pre-computed AI plans (Scout 2.0 §5).
AI_PLANS_DIR = Path("datasets/ai_plans")
from app.services.analysis_generator import (
    confidence_sentence,
    next_move,
    project_blueprints,
    visibility_plan,
)

SYSTEM_PROMPT = (
    "You are Scout, a sharp, practical mentor for developers and AI engineers. "
    "You turn real technology trend signals into a concrete personal action plan. "
    "You are concrete, encouraging, and never generic. "
    "Always answer with a single JSON object and nothing else."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _completions_url(base_url: str) -> str:
    """Resolve a base URL (or HF Space page URL) into the chat completions URL."""
    base = runtime_settings.normalize_base_url(base_url)
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def ai_status() -> dict[str, Any]:
    """Non-secret status used by the public dashboard and /models/status."""
    s = runtime_settings.get_settings()
    return {
        "ai_enabled": bool(s["ai_enabled"]),
        "provider": s["ai_provider"],
        "model": s["ai_model"],
        "base_url": runtime_settings.normalize_base_url(s["ai_base_url"]),
        "api_key_set": bool(s.get("ai_api_key")),
        "fallback": "deterministic templates",
    }


def _chat(messages: list[dict[str, str]], settings: dict[str, Any] | None = None,
          *, max_tokens: int | None = None, temperature: float | None = None) -> str:
    s = settings or runtime_settings.get_settings()
    url = _completions_url(s["ai_base_url"])
    headers = {"Content-Type": "application/json"}
    # OllaBridge's public gateway accepts "not-needed"; a real key is sent as a
    # standard bearer token. Always send one so strict gateways don't 401.
    headers["Authorization"] = f"Bearer {s.get('ai_api_key') or 'not-needed'}"
    payload = {
        "model": s["ai_model"],
        "messages": messages,
        "temperature": s["ai_temperature"] if temperature is None else temperature,
        "max_tokens": s["ai_max_tokens"] if max_tokens is None else max_tokens,
        "stream": False,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=float(s["ai_timeout"]))
    resp.raise_for_status()
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a model reply, tolerating code fences / prose."""
    if not text:
        raise ValueError("empty response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("no JSON object found in model response")


def _signals_brief(topic: dict) -> str:
    signals = topic.get("signals", {}) or {}
    keep = ("github_activity", "github_growth", "huggingface_activity", "news_mentions",
            "job_demand", "community_activity", "local_relevance", "project_potential",
            "career_value")
    parts = [f"{k}={round(float(signals.get(k, 0)))}" for k in keep if signals.get(k)]
    return ", ".join(parts) or "limited signals"


def _str_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out = [str(v).strip() for v in value if str(v).strip()]
    return out[:limit]


def fallback_plan(topic: dict, country: str, city: str | None, goal: str, profile: str) -> dict[str, Any]:
    """Deterministic plan used when AI is off or unavailable. Same shape as AI."""
    move = next_move(topic, goal, profile)
    vis = visibility_plan(topic)
    blueprints = project_blueprints(topic)
    build = blueprints[0] if blueprints else {"title": move["build"]}
    place = f"{city}, {country}" if city else country
    return {
        "topic_id": topic.get("id"),
        "topic_name": topic.get("name"),
        "source": "deterministic",
        "provider": "Scout templates",
        "model": "template-v1",
        "generated_at": _now(),
        "headline": f"{topic.get('name')} is your strongest move in {place} right now.",
        "why_now": topic.get("why_follow") or topic.get("summary") or "",
        "study": move["study"],
        "build": {
            "title": build.get("title", move["build"]),
            "description": build.get("why_it_promotes_you", "A focused proof-of-work project you can ship fast."),
            "stack": build.get("stack", topic.get("skills", [])[:6]),
            "deliverables": build.get("deliverables", ["GitHub repo", "live demo", "short write-up"]),
        },
        "publish": move["publish"] + vis.get("publish_steps", [])[:2],
        "skills": topic.get("skills", [])[:8] or vis.get("skills_to_show", []),
        "risks": topic.get("risks", ["Signals may be incomplete.", "Some trends can be overhyped."]),
        "confidence": confidence_sentence(topic),
    }


def _build_messages(topic: dict, country: str, city: str | None, goal: str, profile: str) -> list[dict[str, str]]:
    place = f"{city}, {country}" if city else country
    context = {
        "topic": topic.get("name"),
        "what_it_is": topic.get("summary") or topic.get("why_follow"),
        "location": place,
        "goal": goal,
        "profile": profile,
        "real_signals": _signals_brief(topic),
        "sources": sorted({s.get("name", "") for s in topic.get("sources", []) if s.get("name")})[:6],
    }
    schema = (
        '{\n'
        '  "headline": "one motivating sentence tailored to the person and place",\n'
        '  "why_now": "2-3 sentences on why this topic matters now, using the signals",\n'
        '  "study": ["3-5 concrete, ordered learning steps"],\n'
        '  "build": {"title": "one specific portfolio project", "description": "what it does and why it impresses",\n'
        '            "stack": ["tools/libraries"], "deliverables": ["repo", "demo", "write-up"]},\n'
        '  "publish": ["3-4 concrete steps to get this seen by the right people"],\n'
        '  "skills": ["5-8 skills this demonstrates"],\n'
        '  "risks": ["2-3 honest risks or pitfalls"],\n'
        '  "confidence": "one sentence on how solid this recommendation is"\n'
        '}'
    )
    user = (
        f"Design a personal action plan from these real trend signals:\n"
        f"{json.dumps(context, ensure_ascii=False)}\n\n"
        f"Return ONLY a JSON object with exactly this shape (no markdown, no commentary):\n{schema}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _assemble_ai_plan(data: dict, topic: dict, country: str, city: str | None,
                      goal: str, profile: str, *, source: str,
                      provider: str, model: str) -> dict[str, Any]:
    """Normalize a model's JSON reply into Scout's stable plan contract."""
    fallback = fallback_plan(topic, country, city, goal, profile)
    build = data.get("build")
    if isinstance(build, str):
        build = {"title": build}
    if not isinstance(build, dict):
        build = fallback["build"]
    return {
        "topic_id": topic.get("id"),
        "topic_name": topic.get("name"),
        "source": source,
        "provider": provider,
        "model": model,
        "generated_at": _now(),
        "headline": str(data.get("headline") or fallback["headline"]).strip(),
        "why_now": str(data.get("why_now") or fallback["why_now"]).strip(),
        "study": _str_list(data.get("study"), 6) or fallback["study"],
        "build": {
            "title": str(build.get("title") or fallback["build"]["title"]).strip(),
            "description": str(build.get("description") or fallback["build"]["description"]).strip(),
            "stack": _str_list(build.get("stack"), 10) or fallback["build"]["stack"],
            "deliverables": _str_list(build.get("deliverables"), 6) or fallback["build"]["deliverables"],
        },
        "publish": _str_list(data.get("publish"), 6) or fallback["publish"],
        "skills": _str_list(data.get("skills"), 10) or fallback["skills"],
        "risks": _str_list(data.get("risks"), 5) or fallback["risks"],
        "confidence": str(data.get("confidence") or fallback["confidence"]).strip(),
    }


def live_plan(topic: dict, country: str, city: str | None, goal: str, profile: str,
              settings: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Narrate a plan with the live gateway. Returns ``None`` on any failure —
    no template fallback here, so callers (serving and the nightly batch) can
    decide what to do next. This is the single place that calls the LLM."""
    s = settings or runtime_settings.get_settings()
    if not s.get("ai_enabled"):
        return None
    try:
        raw = _chat(_build_messages(topic, country, city, goal, profile), s)
        data = _extract_json(raw)
    except Exception:  # noqa: BLE001 — never break the product on AI errors
        return None
    return _assemble_ai_plan(data, topic, country, city, goal, profile,
                             source="ollabridge-cloud", provider=s["ai_provider"], model=s["ai_model"])


# --- Nightly AI-batch (Scout 2.0 §5–6): pre-compute plans into the dataset ---

def batch_key(topic_id: str | None, country: str, city: str | None,
              goal: str, profile: str) -> str:
    """Stable filename slug for a (topic × location × goal × profile) cell."""
    def slug(v: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", (v or "").lower()).strip("-") or "-"
    parts = [topic_id or "topic", country or "worldwide", city or "any", goal or "any", profile or "any"]
    return "__".join(slug(p) for p in parts)


def batch_content_hash(topic: dict, country: str, city: str | None,
                       goal: str, profile: str) -> str:
    """Hash of the inputs that determine a plan — used to skip re-narrating cells
    whose deterministic ranking did not change since the last run (cost control)."""
    payload = {
        "topic_id": topic.get("id"),
        "signals": topic.get("signals", {}),
        "rank": topic.get("rank"),
        "country": country, "city": city, "goal": goal, "profile": profile,
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load_batch_plan(topic: dict, country: str, city: str | None, goal: str, profile: str,
                    base_dir: Path | None = None) -> dict[str, Any] | None:
    """Load a pre-computed nightly plan for this cell, if one exists."""
    directory = base_dir or AI_PLANS_DIR
    path = directory / (batch_key(topic.get("id"), country, city, goal, profile) + ".json")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    data["source"] = "ai-batch"
    return data


def generate_plan(topic: dict, country: str, city: str | None,
                  goal: str, profile: str) -> dict[str, Any]:
    """Serving order (Scout 2.0 §6.1): live AI → nightly AI-batch → deterministic
    template. The ``source`` field says which engine produced the plan, so the
    static site can serve real AI output from the dataset with no live backend."""
    settings = runtime_settings.get_settings()

    # 1. live AI, when the gateway is enabled and reachable
    plan = live_plan(topic, country, city, goal, profile, settings)
    if plan is not None:
        return plan

    # 2. nightly AI-batch plan pre-computed into the dataset
    batch = load_batch_plan(topic, country, city, goal, profile)
    if batch is not None:
        return batch

    # 3. deterministic template — true last resort
    fallback = fallback_plan(topic, country, city, goal, profile)
    fallback["note"] = ("AI is disabled." if not settings["ai_enabled"]
                        else "AI unavailable; showing Scout's built-in plan.")
    return fallback


def test_connection(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Quick health check used by the admin Settings page."""
    s = settings or runtime_settings.get_settings()
    started = datetime.now(timezone.utc)
    try:
        reply = _chat(
            [{"role": "user", "content": "Reply with exactly the word: pong"}],
            s,
            max_tokens=16,
            temperature=0.0,
        )
        latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        return {
            "ok": True,
            "provider": s["ai_provider"],
            "model": s["ai_model"],
            "base_url": s["ai_base_url"],
            "latency_ms": round(latency),
            "sample": reply[:120],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "provider": s["ai_provider"],
            "model": s["ai_model"],
            "base_url": s["ai_base_url"],
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }
