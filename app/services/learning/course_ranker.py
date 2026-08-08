"""Course ranker — score only real, retrieved, normalized resources.

The LLM never picks courses from an unranked list. First apply hard filters
(language, budget, level, URL, prerequisites), then compute a transparent score
with mode-specific weights, returning both the score and human-readable reasons
and warnings (spec section 10).
"""
from __future__ import annotations

from app.services.learning.schemas import (
    LearningGoalRequest,
    LearningResource,
    RankedResource,
    SkillGap,
)

_LEVEL_RANK = {"unknown": 0, "beginner": 1, "intermediate": 2, "advanced": 3}

# Mode weights (must each sum to 1.0). Keys are score components.
_WEIGHTS: dict[str, dict[str, float]] = {
    "topic": {
        "skill_coverage": 0.30, "prerequisite_fit": 0.15, "level_fit": 0.15,
        "quality": 0.10, "project": 0.10, "schedule_fit": 0.10,
        "budget_fit": 0.05, "freshness": 0.05,
    },
    "certification": {
        "domain_coverage": 0.30, "authority": 0.20, "assessment": 0.15,
        "labs": 0.10, "level_fit": 0.10, "freshness": 0.10, "budget_fit": 0.05,
    },
    "career": {
        "skill_coverage": 0.25, "demand": 0.20, "prerequisite_fit": 0.15,
        "portfolio": 0.10, "quality": 0.10, "durability": 0.10,
        "certification_value": 0.05, "budget_fit": 0.05,
    },
}

_AUTHORITATIVE = {"microsoft_learn", "openedx", "credential_engine"}


def _blocked(resource: LearningResource, req: LearningGoalRequest) -> str | None:
    """Return a rejection reason, or ``None`` if the resource passes hard filters."""
    prefs = {p.lower() for p in req.preferred_providers}
    if not resource.url:
        return "no accessible URL"
    if req.language and resource.language:
        want = req.language.lower()[:2]
        if want and resource.language.lower()[:2] != want and want != "en":
            # We only hard-block when the learner asked for a non-English course
            # and the resource is clearly a different language.
            if resource.language.lower()[:2] != want:
                return "language mismatch"
    if req.budget.free_only and resource.access.type not in {"free", "free_audit", "free_preview"}:
        # A search-discovered "unknown" cannot be assumed free.
        if resource.access.type == "unknown":
            return "cannot verify free access (free_only requested)"
        if resource.access.type not in {"free", "free_audit", "free_preview"}:
            return "not free (free_only requested)"
    if (req.budget.maximum is not None and resource.access.price is not None
            and resource.access.observed_at
            and resource.access.price > req.budget.maximum):
        return "over budget"
    return None


def _covered_skills(resource: LearningResource, gap: SkillGap) -> set[str]:
    return set(resource.skills_taught) & set(gap.missing_skill_ids)


def _level_fit(resource: LearningResource, req: LearningGoalRequest) -> float:
    if resource.level == "unknown":
        return 0.5
    learner = max((_LEVEL_RANK.get(s.level, 0) for s in req.current_skills), default=1)
    diff = abs(_LEVEL_RANK.get(resource.level, 1) - max(learner, 1))
    return max(0.0, 1.0 - 0.35 * diff)


def _budget_fit(resource: LearningResource, req: LearningGoalRequest) -> float:
    if resource.access.type in {"free", "free_audit"}:
        return 1.0
    if resource.access.type == "unknown":
        return 0.4
    if req.budget.maximum is None or resource.access.price is None:
        return 0.6
    return 1.0 if resource.access.price <= req.budget.maximum else 0.2


def _freshness(resource: LearningResource) -> float:
    return 0.9 if resource.provenance.last_verified_at else 0.5


def score_resource(
    resource: LearningResource,
    gap: SkillGap,
    req: LearningGoalRequest,
    mode: str,
) -> RankedResource:
    covered = _covered_skills(resource, gap)
    coverage_frac = (len(covered) / len(gap.missing_skill_ids)) if gap.missing_skill_ids else 0.0
    # Cap coverage credit so a single course can't dominate purely on breadth.
    coverage = min(1.0, len(covered) / 3) if covered else 0.0

    prereq_ok = set(resource.prerequisite_skills).issubset(
        set(gap.known_skill_ids) | set(gap.missing_skill_ids))
    components = {
        "skill_coverage": coverage,
        "domain_coverage": coverage,
        "prerequisite_fit": 1.0 if prereq_ok else 0.3,
        "level_fit": _level_fit(resource, req),
        "quality": resource.quality.evidence_confidence,
        "authority": 1.0 if resource.provider in _AUTHORITATIVE else 0.4,
        "assessment": 1.0 if resource.has_assessments else 0.3,
        "labs": 1.0 if resource.has_projects else 0.3,
        "project": 1.0 if resource.has_projects else 0.4,
        "portfolio": 1.0 if resource.has_projects else 0.4,
        "schedule_fit": 1.0 if (resource.duration_minutes or 0) <= req.hours_per_week * 60 * 3 else 0.6,
        "budget_fit": _budget_fit(resource, req),
        "freshness": _freshness(resource),
        "demand": 0.6,  # neutral without a live demand signal in Phase 1
        "durability": 0.7,
        "certification_value": 1.0 if resource.certification_alignment else 0.3,
    }
    weights = _WEIGHTS.get(mode, _WEIGHTS["topic"])
    raw = sum(weights[k] * components.get(k, 0.0) for k in weights)
    score = round(raw * 100, 1)

    reasons: list[str] = []
    if covered:
        names = ", ".join(sorted(covered))
        reasons.append(f"Covers {len(covered)} needed skill(s): {names}.")
    if resource.has_projects:
        reasons.append("Includes a practical project or lab.")
    if resource.has_assessments:
        reasons.append("Includes assessments to check understanding.")
    if resource.provider in _AUTHORITATIVE:
        reasons.append(f"From an authoritative source ({resource.provider}).")
    if _level_fit(resource, req) >= 0.75 and resource.level != "unknown":
        reasons.append(f"Matches your level ({resource.level}).")

    warnings: list[str] = []
    if resource.access.type == "unknown" or resource.access.observed_at is None:
        warnings.append("Current price/access could not be verified — verify on provider.")
    if resource.quality.rating is None:
        warnings.append("No independent rating was found.")
    if resource.provenance.source_type == "web_search":
        warnings.append("Search-discovered; details are not from an official catalog.")
    if not prereq_ok:
        warnings.append("Lists prerequisites outside this plan.")

    return RankedResource(resource=resource, score=score, reasons=reasons, warnings=warnings)


def rank(
    resources: list[LearningResource],
    gap: SkillGap,
    req: LearningGoalRequest,
    mode: str = "topic",
) -> list[RankedResource]:
    """Filter then score. Returns ranked resources, highest score first."""
    ranked: list[RankedResource] = []
    for resource in resources:
        if _blocked(resource, req):
            continue
        ranked.append(score_resource(resource, gap, req, mode))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked
