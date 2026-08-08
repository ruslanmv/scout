"""Plan narrator — turn a valid path into learner-friendly language.

Runs *after* the deterministic optimizer. It may call the AI gateway to write a
warmer rationale, but it only ever rewrites *narrative* fields (the summary and
confidence). It never invents or alters courses, prices, ratings, exam codes or
the stage sequence — those come from evidence (spec sections 11, 13, 17).

If AI is disabled or unreachable, a deterministic summary is used, so the
contract returned to the frontend is identical either way.
"""
from __future__ import annotations

import json

from app.services.learning.schemas import (
    LearningGoalRequest,
    LearningPath,
    PathRationale,
    ResolvedGoal,
)


def _deterministic_summary(path: LearningPath, resolved: ResolvedGoal) -> str:
    n = len(path.stages)
    weeks = path.duration.estimated_weeks
    goal = path.resolved_goal.title
    covered = sorted({s for stage in path.stages for s in stage.skills})
    lead = ", ".join(covered[:4])
    return (
        f"A {n}-stage path toward {goal}, about {weeks:g} weeks at "
        f"{path.duration.hours_per_week:g} h/week. It builds "
        f"{lead}{' and more' if len(covered) > 4 else ''} in prerequisite order, "
        f"each stage ending in a project or checkpoint."
    )


def _confidence(path: LearningPath) -> float:
    if not path.stages:
        return 0.3
    verified = sum(1 for s in path.stages for r in s.resources
                   if r.primary.resource.provenance.last_verified_at)
    total_res = sum(len(s.resources) for s in path.stages) or 1
    base = 0.5 + 0.3 * (verified / total_res)
    if path.uncovered_skills:
        base -= 0.15
    return round(min(0.95, max(0.3, base)), 2)


def narrate(
    path: LearningPath,
    resolved: ResolvedGoal,
    req: LearningGoalRequest,
    *,
    use_ai: bool = False,
) -> LearningPath:
    summary = _deterministic_summary(path, resolved)
    confidence = _confidence(path)
    location_effect = resolved.location_effect
    source = path.source

    if use_ai:
        try:
            from app.services import ai_advisor, runtime_settings

            settings = runtime_settings.get_settings()
            if settings.get("ai_enabled"):
                context = {
                    "goal": path.resolved_goal.title,
                    "stages": [s.title for s in path.stages],
                    "skills": sorted({sk for s in path.stages for sk in s.skills}),
                    "weeks": path.duration.estimated_weeks,
                    "hours_per_week": path.duration.hours_per_week,
                    "current_role": req.current_role,
                }
                messages = [
                    {"role": "system", "content": (
                        "You are Scout, a practical learning mentor. You are given a "
                        "fixed, evidence-based learning path. Write ONLY a short "
                        "motivating summary of it. Do NOT invent courses, prices, "
                        "ratings, or change the sequence. Reply with a JSON object "
                        '{"summary": "..."} and nothing else.')},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ]
                raw = ai_advisor._chat(messages, settings, max_tokens=220, temperature=0.4)
                data = ai_advisor._extract_json(raw)
                ai_summary = str(data.get("summary") or "").strip()
                if ai_summary:
                    summary = ai_summary
                    source = settings.get("ai_provider") or "ai"
        except Exception:  # noqa: BLE001 — never break the product on AI errors
            pass  # keep the deterministic summary

    path.rationale = PathRationale(
        summary=summary,
        location_effect=location_effect,
        confidence=confidence,
    )
    path.source = source
    return path
