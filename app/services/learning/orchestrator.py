"""Learning Path Orchestrator — the deterministic pipeline (spec section 22).

    understand the user
        -> resolve the target
        -> calculate the skill gap
        -> retrieve real resources
        -> verify and normalize them
        -> rank them deterministically
        -> optimize the sequence
        -> ask AI to explain and personalize it
        -> validate the output

AI improves the experience; deterministic logic, evidence and fallbacks keep the
product reliable. Resolved goals and generated paths are held in a small
in-process store so the API can support ``GET``, ``replan`` and ``progress``.
"""
from __future__ import annotations

import uuid

from app.providers import base as providers
from app.services.learning import (
    cert_track,
    certifications,
    course_ranker,
    fallback,
    goal_resolver,
    path_optimizer,
    plan_narrator,
    skill_gap,
    taxonomy,
    validator,
)
from app.services.learning.schemas import (
    GoalCandidate,
    LearningGoalRequest,
    LearningPath,
    ProgressEvent,
    ResolvedGoal,
    ResourceQuery,
    SkillGap,
)

# --- In-process stores (Phase 1). Phase 2 swaps these for PostgreSQL. --------
_GOALS: dict[str, ResolvedGoal] = {}
_PATHS: dict[str, LearningPath] = {}
_PROGRESS: dict[str, list[ProgressEvent]] = {}


def _mode_for(goal: GoalCandidate) -> str:
    if goal.type == "certification":
        return "certification"
    if goal.type == "career_transition":
        return "career"
    return "topic"


# --- Pipeline steps ---------------------------------------------------------

def resolve_goal(req: LearningGoalRequest) -> ResolvedGoal:
    resolved = goal_resolver.resolve(req)
    _GOALS[resolved.id] = resolved
    return resolved


def evaluate_skill_gap(goal: GoalCandidate, req: LearningGoalRequest) -> SkillGap:
    return skill_gap.calculate(goal, req)


def skill_gap_for_request(
    req: LearningGoalRequest,
    resolved_goal_id: str | None = None,
) -> tuple[GoalCandidate, SkillGap]:
    """Resolve the goal (or reuse a stored one) and compute its skill gap."""
    goal = _goal_for_request(req, resolved_goal_id)
    return goal, skill_gap.calculate(goal, req)


def search_resources(req: LearningGoalRequest, skills: list[str] | None = None):
    """Retrieve + normalize resources across all providers for a query."""
    query = ResourceQuery(
        text=req.query,
        skills=skills or [],
        language=(req.language or "en").lower()[:2] or "en",
        providers=req.preferred_providers,
        free_only=req.budget.free_only,
        limit=40,
    )
    return providers.search_all(query)


def _goal_for_request(req: LearningGoalRequest, resolved_goal_id: str | None) -> GoalCandidate:
    if resolved_goal_id and resolved_goal_id in _GOALS:
        return _GOALS[resolved_goal_id].recommended
    return resolve_goal(req).recommended


def generate_path(
    req: LearningGoalRequest,
    *,
    resolved_goal_id: str | None = None,
    use_ai: bool = False,
) -> LearningPath:
    """Run the full deterministic pipeline and return a validated path."""
    goal = _goal_for_request(req, resolved_goal_id)
    gap = evaluate_skill_gap(goal, req)
    mode = _mode_for(goal)
    path_id = f"path_{uuid.uuid4().hex[:12]}"

    cert = (certifications.get_certification(goal.target_certification)
            if goal.target_certification else None)
    if mode == "certification" and cert is not None:
        # Certification prep gets a purpose-built, typed study track rather than a
        # flat set-cover (training -> build -> pillars -> exam guide -> practice
        # -> community -> projects -> register).
        path = cert_track.build_cert_path(path_id, goal, gap, req, cert)
        if not path.stages:
            path = fallback.build_fallback_path(path_id, goal, gap, req)
    else:
        resources = search_resources(req, skills=gap.missing_skill_ids)
        ranked = course_ranker.rank(resources, gap, req, mode=mode)
        if ranked and gap.missing_skill_ids:
            path = path_optimizer.build_path(path_id, goal, gap, ranked, req)
            if not path.stages:  # everything filtered out at selection time
                path = fallback.build_fallback_path(path_id, goal, gap, req)
        else:
            path = fallback.build_fallback_path(path_id, goal, gap, req)

    # Attach the resolved goal's alternatives, if we have them.
    resolved = _GOALS.get(resolved_goal_id or "")
    if resolved:
        path.alternatives = resolved.alternatives
        if resolved.location_effect and not path.rationale.location_effect:
            path.rationale.location_effect = resolved.location_effect

    path = plan_narrator.narrate(path, resolved or _synth_resolved(goal, req), req, use_ai=use_ai)
    ok, warnings = validator.validate(path)
    path.warnings = warnings
    if not ok:
        # A hard violation means we cannot trust the optimized path — fall back.
        fb = fallback.build_fallback_path(path_id, goal, gap, req)
        fb.warnings = warnings + fb.warnings
        path = plan_narrator.narrate(fb, resolved or _synth_resolved(goal, req), req, use_ai=False)

    _assign_stage_ids(path)
    _PATHS[path.path_id] = path
    _PROGRESS.setdefault(path.path_id, [])
    return path


def _slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text.strip()]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:40] or "stage"


def _assign_stage_ids(path: LearningPath) -> None:
    """Give every stage a stable id so a portal (and replanning) can key on it
    rather than a bare stage number that shifts when the path changes."""
    for stage in path.stages:
        if not stage.stage_id:
            stage.stage_id = f"s{stage.stage}-{_slug(stage.title)}"


def _synth_resolved(goal: GoalCandidate, req: LearningGoalRequest) -> ResolvedGoal:
    return ResolvedGoal(id=f"goal_{uuid.uuid4().hex[:8]}", query=req.query,
                        intent=req.intent, recommended=goal)


# --- Store operations -------------------------------------------------------

def get_path(path_id: str) -> LearningPath | None:
    return _PATHS.get(path_id)


def record_progress(event: ProgressEvent) -> LearningPath | None:
    path = _PATHS.get(event.path_id)
    if not path:
        return None
    _PROGRESS.setdefault(event.path_id, []).append(event)
    return path


def get_progress(path_id: str) -> list[ProgressEvent]:
    return _PROGRESS.get(path_id, [])


def replan(path_id: str, req: LearningGoalRequest, *, use_ai: bool = False) -> LearningPath | None:
    """Regenerate a path, folding completed stages into the learner's known skills."""
    old = _PATHS.get(path_id)
    if not old:
        return None
    completed_stages = {e.stage for e in get_progress(path_id)
                        if e.status == "completed"}
    # Treat completed stages' skills as already known so replanning skips them.
    from app.services.learning.schemas import SkillRef

    learned = [SkillRef(name=s, level="intermediate")
               for stage in old.stages if stage.stage in completed_stages
               for s in stage.skills]
    enriched = req.model_copy(deep=True)
    enriched.current_skills = list(enriched.current_skills) + learned
    new_path = generate_path(enriched, use_ai=use_ai)
    new_path.replan_after = {"completed_stages": len(completed_stages)}
    _PATHS[new_path.path_id] = new_path
    return new_path


# --- Read helpers for the API / MCP -----------------------------------------

def provider_health():
    return providers.provider_health()


def search_skills(query: str, limit: int = 10):
    return taxonomy.search_skills(query, limit)


def search_occupations(query: str, limit: int = 10):
    return taxonomy.search_occupations(query, limit)


def search_certifications(query: str, limit: int = 10):
    return certifications.search_certifications(query, limit)
