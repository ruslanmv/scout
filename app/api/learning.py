"""Learning Navigator API (spec section 14).

Deterministic, evidence-backed learning-path endpoints:

    POST /learning/goals/resolve
    POST /learning/resources/search
    POST /learning/paths
    GET  /learning/paths/{path_id}
    POST /learning/paths/{path_id}/replan
    PATCH /learning/paths/{path_id}/progress
    GET  /skills/search
    GET  /occupations/search
    GET  /certifications/search
    GET  /providers/health

Path generation runs the full deterministic pipeline synchronously and returns a
completed plan — it never holds the request on a live LLM call (AI narration is
opt-in via ``use_ai`` and always falls back to deterministic text).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.learning import orchestrator, taxonomy
from app.services.learning.schemas import (
    Budget,
    LearningGoalRequest,
    ProgressEvent,
    ResourceQuery,
)

router = APIRouter(tags=["learning"])


# --- Goals ------------------------------------------------------------------

@router.post("/learning/goals/resolve")
def resolve_goal(req: LearningGoalRequest):
    """Refine a vague request into a recommended target plus alternatives."""
    resolved = orchestrator.resolve_goal(req)
    return {
        "goal_id": resolved.id,
        "recommended": {
            "id": resolved.recommended.id,
            "title": resolved.recommended.title,
            "type": resolved.recommended.type,
            "reason": resolved.recommended.reason,
            "target_role": resolved.recommended.target_role,
            "target_certification": resolved.recommended.target_certification,
        },
        "alternatives": [
            {"id": a.id, "title": a.title, "type": a.type, "reason": a.reason}
            for a in resolved.alternatives
        ],
        "location_effect": resolved.location_effect,
        "generated_at": resolved.generated_at,
    }


# --- Resource search --------------------------------------------------------

@router.post("/learning/resources/search")
def search_resources(query: ResourceQuery):
    """Retrieve and normalize resources across every provider for a query."""
    from app.providers import base as providers

    results = providers.search_all(query)
    return {
        "count": len(results),
        "resources": [r.model_dump() for r in results],
    }


# --- Skill gap (Phase 2 — powers the UI skill-gap map) ----------------------

class SkillGapRequest(BaseModel):
    request: LearningGoalRequest | None = None
    resolved_goal_id: str | None = None


@router.post("/learning/skill-gap")
def evaluate_skill_gap(body: SkillGapRequest):
    """Resolve the goal and return the learner's skill gap (known vs missing,
    in topological learning order, with local-demand-aware priority)."""
    req = body.request or LearningGoalRequest()
    goal, gap = orchestrator.skill_gap_for_request(req, body.resolved_goal_id)
    return {
        "goal": {"id": goal.id, "title": goal.title, "type": goal.type},
        "known": [{"skill_id": i.skill_id, "name": i.name} for i in gap.required
                  if i.already_known],
        "missing": [{"skill_id": i.skill_id, "name": i.name, "level": i.level,
                     "priority": i.priority, "reason": i.reason}
                    for i in gap.required if not i.already_known],
        "ordered_skill_ids": gap.ordered_skill_ids,
    }


@router.get("/skills/graph")
def skills_graph(skills: str = Query("", description="Comma-separated skill ids to focus on")):
    """Return a nodes/edges view of the skill graph for visualization."""
    focus = [s.strip() for s in skills.split(",") if s.strip()] or None
    return taxonomy.graph(focus)


# --- Paths ------------------------------------------------------------------

class GeneratePathRequest(BaseModel):
    request: LearningGoalRequest | None = None
    resolved_goal_id: str | None = None
    hours_per_week: float | None = None
    budget: Budget | None = None
    use_ai: bool = False


@router.post("/learning/paths")
def create_path(body: GeneratePathRequest):
    req = body.request or LearningGoalRequest()
    if body.hours_per_week is not None:
        req.hours_per_week = body.hours_per_week
    if body.budget is not None:
        req.budget = body.budget
    if not (req.query or req.target_role or req.target_certification or body.resolved_goal_id):
        raise HTTPException(
            status_code=422,
            detail="Provide a query, target_role, target_certification, or resolved_goal_id.")
    path = orchestrator.generate_path(
        req, resolved_goal_id=body.resolved_goal_id, use_ai=body.use_ai)
    return path.model_dump()


@router.get("/learning/paths/{path_id}")
def get_path(path_id: str):
    path = orchestrator.get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found.")
    return path.model_dump()


class ReplanRequest(BaseModel):
    request: LearningGoalRequest | None = None
    use_ai: bool = False


@router.post("/learning/paths/{path_id}/replan")
def replan_path(path_id: str, body: ReplanRequest):
    req = body.request or LearningGoalRequest()
    path = orchestrator.replan(path_id, req, use_ai=body.use_ai)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found.")
    return path.model_dump()


class ProgressUpdate(BaseModel):
    stage: int
    status: str = "completed"
    score: float | None = None
    note: str | None = None


@router.patch("/learning/paths/{path_id}/progress")
def update_progress(path_id: str, body: ProgressUpdate):
    event = ProgressEvent(
        path_id=path_id, stage=body.stage, status=body.status,  # type: ignore[arg-type]
        score=body.score, note=body.note)
    path = orchestrator.record_progress(event)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found.")
    return {
        "path_id": path_id,
        "recorded": event.model_dump(),
        "progress": [e.model_dump() for e in orchestrator.get_progress(path_id)],
    }


# --- Knowledge lookups ------------------------------------------------------

@router.get("/skills/search")
def skills_search(q: str = Query("", description="Skill name or keyword"),
                  limit: int = 10):
    return {"query": q, "results": [s.model_dump() for s in orchestrator.search_skills(q, limit)]}


@router.get("/occupations/search")
def occupations_search(q: str = Query("", description="Occupation name or keyword"),
                       limit: int = 10):
    return {"query": q,
            "results": [o.model_dump() for o in orchestrator.search_occupations(q, limit)]}


@router.get("/certifications/search")
def certifications_search(q: str = Query("", description="Certification name, code or issuer"),
                          limit: int = 10):
    return {"query": q,
            "results": [c.model_dump() for c in orchestrator.search_certifications(q, limit)]}


@router.get("/providers/health")
def providers_health():
    return {"providers": [h.model_dump() for h in orchestrator.provider_health()]}
