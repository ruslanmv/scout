"""Skill-gap service — resolve prerequisites and missing competencies.

Given a resolved goal and the learner's current skills, compute the full set of
required skills (target skills plus all transitive prerequisites), mark which the
learner already has, and order the rest topologically so prerequisites always
come first (spec sections 8, 11).
"""
from __future__ import annotations

from app.services.learning import taxonomy
from app.services.learning.schemas import (
    GoalCandidate,
    LearningGoalRequest,
    SkillGap,
    SkillGapItem,
)

def _known_skill_ids(req: LearningGoalRequest) -> set[str]:
    # ``current_skills`` are skills the learner already has, so listing one means
    # it is known — the level modulates depth, not presence. Knowing a skill also
    # implies its prerequisites are covered.
    known: set[str] = set()
    for ref in req.current_skills:
        node = taxonomy.resolve_skill(ref.name)
        if node:
            known.add(node.id)
            known.update(taxonomy.expand_prerequisites([node.id]))
    return known


def _local_demand_boost(req: LearningGoalRequest, skill_id: str) -> float:
    """Small, explainable priority nudge from local demand (spec section 8).

    Never changes ordering (that stays prerequisite-driven) — only relative
    priority within the missing set.
    """
    if not req.use_location or not req.country:
        return 0.0
    from app.services.learning.goal_resolver import _LOCATION_DEMAND

    demand = _LOCATION_DEMAND.get(req.country.strip().lower())
    if not demand:
        return 0.0
    node = taxonomy.get_skill(skill_id)
    if not node:
        return 0.0
    hay = " ".join([node.name] + node.aliases).lower()
    return 0.15 if any(term.lower() in hay for term in demand) else 0.0


def calculate(goal: GoalCandidate, req: LearningGoalRequest) -> SkillGap:
    required_ids = taxonomy.expand_prerequisites(list(goal.skills))
    known = _known_skill_ids(req)
    ordered = taxonomy.topological_sort(required_ids)

    items: list[SkillGapItem] = []
    missing: list[str] = []
    for sid in ordered:
        node = taxonomy.get_skill(sid)
        if node is None:
            continue
        already = sid in known
        if not already:
            missing.append(sid)
        # Priority combines skill durability, career relevance to the goal and
        # local demand. Durable, in-scope skills rank higher.
        relevance = 1.0 if sid in goal.skills else 0.6
        priority = round(
            node.durability * 0.5 + relevance * 0.5 + _local_demand_boost(req, sid), 3)
        items.append(SkillGapItem(
            skill_id=sid,
            name=node.name,
            level=node.level,
            priority=priority,
            already_known=already,
            reason=("Already covered by your current skills." if already
                    else f"Required for {goal.title}."),
        ))

    return SkillGap(
        goal_id=goal.id,
        required=items,
        ordered_skill_ids=ordered,
        known_skill_ids=[i.skill_id for i in items if i.already_known],
        missing_skill_ids=missing,
    )
