"""Goal resolver — turn a vague request into concrete learning targets.

Deterministic, offline, and explainable. It maps the learner's free-text query
(and intent) onto one or more complete targets from the internal taxonomy, and
explains any location effect without ever claiming location changes technical
prerequisites (spec sections 2, 3, 8).
"""
from __future__ import annotations

import uuid

from app.services.learning import certifications, taxonomy
from app.services.learning.schemas import (
    GoalCandidate,
    LearningGoalRequest,
    ResolvedGoal,
)

# Markets where these skills see notably higher demand (illustrative, aggregate
# only — never individual data, spec section 17). Used solely to *explain* a
# recommendation, not to alter prerequisites.
_LOCATION_DEMAND: dict[str, list[str]] = {
    "italy": ["Azure", "cloud security", "data engineering"],
    "germany": ["cloud", "industrial AI", "data engineering"],
    "united states": ["generative AI", "ML platforms", "agents"],
    "united kingdom": ["AI safety", "cloud", "fintech ML"],
}


def _score_target(target: dict, query: str) -> int:
    q = (query or "").lower()
    score = 0
    for kw in target.get("keywords", []):
        if kw in q:
            score += 2
    for word in q.split():
        if len(word) > 2 and any(word in kw for kw in target.get("keywords", [])):
            score += 1
    if target["title"].lower() in q:
        score += 3
    return score


def _location_effect(req: LearningGoalRequest) -> str | None:
    if not req.use_location or not req.country:
        return None
    demand = _LOCATION_DEMAND.get(req.country.strip().lower())
    if not demand:
        return None
    where = f"{req.city}, {req.country}" if req.city else req.country
    return (
        f"Location influenced this recommendation because demand for "
        f"{', '.join(demand)} is higher in {where}. Location affects which "
        f"specialization and skills are emphasized — not the technical "
        f"prerequisites or the order in which you must learn them."
    )


def _cert_candidate(req: LearningGoalRequest) -> GoalCandidate | None:
    name = req.target_certification or req.query
    cert = certifications.resolve_certification(name)
    if not cert:
        return None
    return GoalCandidate(
        id=cert.id,
        title=cert.name,
        type="certification",
        reason=(f"Official {cert.issuer} certification"
                + (f" (exam {cert.exam_code})" if cert.exam_code else "")
                + ". Study time is weighted by the official exam domains."),
        target_certification=cert.id,
        skills=cert.skills(),
    )


def _career_candidate(req: LearningGoalRequest) -> GoalCandidate | None:
    name = req.target_role or req.query
    occ = taxonomy.resolve_occupation(name)
    if not occ:
        return None
    skills = list(occ.core_skills) + list(occ.specializations)
    return GoalCandidate(
        id=f"occupation-goal:{occ.id.split(':', 1)[-1]}",
        title=f"Become a {occ.name}",
        type="career_transition",
        reason=f"Targets the core skills employers expect from a {occ.name}.",
        target_role=occ.name,
        skills=skills,
    )


def resolve(req: LearningGoalRequest) -> ResolvedGoal:
    """Resolve ``req`` into a recommended target plus alternatives."""
    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    location_effect = _location_effect(req)

    recommended: GoalCandidate | None = None
    alternatives: list[GoalCandidate] = []

    if req.intent == "prepare_certification":
        recommended = _cert_candidate(req)
    elif req.intent == "advance_career":
        recommended = _career_candidate(req)

    # Rank taxonomy learning targets by keyword overlap for topic / discovery
    # intents, and as alternatives for the specialized intents.
    ranked = sorted(
        taxonomy.learning_targets(),
        key=lambda t: _score_target(t, req.query or req.target_role or ""),
        reverse=True,
    )
    target_candidates = [taxonomy.target_to_candidate(t) for t in ranked]

    if recommended is None:
        recommended = target_candidates[0]
        alternatives = target_candidates[1:3]
    else:
        alternatives = target_candidates[:2]

    return ResolvedGoal(
        id=goal_id,
        query=req.query,
        intent=req.intent,
        recommended=recommended,
        alternatives=alternatives,
        location_effect=location_effect,
    )
