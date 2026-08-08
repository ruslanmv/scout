"""Deterministic learning-path optimizer (spec section 11).

After ranking, a weighted set-cover selects the smallest strong set of resources
that covers the missing skills without violating prerequisites, then schedules
them into stages sized to the learner's weekly time budget. No LLM is involved —
this is the reliable core the AI later narrates.
"""
from __future__ import annotations

from app.services.learning import taxonomy
from app.services.learning.schemas import (
    LearningGoalRequest,
    LearningPath,
    LearningStage,
    PathDuration,
    RankedResource,
    SkillGap,
    StageAssessment,
    StageProject,
    StageResource,
)


def _marginal_value(
    candidate: RankedResource,
    remaining: set[str],
    completed: set[str],
) -> float:
    """Value of adding a candidate: newly covered skills, weighted by its score,
    penalized when it teaches skills whose prerequisites are not yet covered.
    """
    taught = set(candidate.resource.skills_taught)
    newly = taught & remaining
    if not newly:
        return -1.0
    penalty = 0.0
    for sid in newly:
        node = taxonomy.get_skill(sid)
        if not node:
            continue
        unmet = [p for p in node.prerequisites if p not in completed and p not in taught]
        penalty += 0.5 * len(unmet)
    return len(newly) + candidate.score / 100.0 - penalty


def select_resources(
    ranked: list[RankedResource],
    gap: SkillGap,
) -> tuple[list[RankedResource], list[str]]:
    """Weighted set-cover. Returns (selected, uncovered_skill_ids)."""
    remaining = set(gap.missing_skill_ids)
    completed = set(gap.known_skill_ids)
    pool = list(ranked)
    selected: list[RankedResource] = []

    while remaining:
        best: RankedResource | None = None
        best_value = 0.0
        for cand in pool:
            if cand in selected:
                continue
            value = _marginal_value(cand, remaining, completed)
            if value > best_value:
                best_value, best = value, cand
        if best is None:
            break
        selected.append(best)
        newly = set(best.resource.skills_taught) & remaining
        remaining -= newly
        completed |= set(best.resource.skills_taught)

    return selected, sorted(remaining)


def _cheaper_alternative(
    primary: RankedResource,
    ranked: list[RankedResource],
    used_ids: set[str],
) -> RankedResource | None:
    """Find a free/cheaper resource covering the same primary skill (spec §12)."""
    primary_skills = set(primary.resource.skills_taught)
    primary_free = primary.resource.access.type in {"free", "free_audit"}
    for cand in ranked:
        if cand.resource.id in used_ids or cand.resource.id == primary.resource.id:
            continue
        if not (set(cand.resource.skills_taught) & primary_skills):
            continue
        cand_free = cand.resource.access.type in {"free", "free_audit"}
        if cand_free and not primary_free:
            return cand
        # Same access tier: only surface a materially different alternative.
        if cand_free and primary_free:
            return cand
    return None


def _order_selected(selected: list[RankedResource], gap: SkillGap) -> list[RankedResource]:
    """Order chosen resources so every prerequisite is scheduled first.

    A resource must come no earlier than the *latest* skill it teaches in the
    topological order — otherwise a course that bundles an advanced skill with an
    easy one could be pulled forward ahead of that skill's prerequisites.
    """
    rank_of = {sid: i for i, sid in enumerate(gap.ordered_skill_ids)}

    def key(rr: RankedResource) -> tuple[float, float, str]:
        skills = [rank_of[s] for s in rr.resource.skills_taught if s in rank_of]
        latest = max(skills) if skills else -1.0
        earliest = min(skills) if skills else -1.0
        return (latest, earliest, rr.resource.title)

    return sorted(selected, key=key)


def build_path(
    path_id: str,
    goal,
    gap: SkillGap,
    ranked: list[RankedResource],
    req: LearningGoalRequest,
) -> LearningPath:
    selected, uncovered = select_resources(ranked, gap)
    selected = _order_selected(selected, gap)

    hours_per_week = max(1.0, float(req.hours_per_week or 8))
    stages: list[LearningStage] = []
    used_ids: set[str] = {rr.resource.id for rr in selected}
    covered_so_far: set[str] = set(gap.known_skill_ids)
    sources: list[dict] = []

    for i, rr in enumerate(selected, start=1):
        res = rr.resource
        stage_skills = [s for s in res.skills_taught if s in gap.missing_skill_ids]
        prereqs = sorted({p for s in stage_skills for p in (taxonomy.get_skill(s).prerequisites
                          if taxonomy.get_skill(s) else []) if p in covered_so_far})
        alt = _cheaper_alternative(rr, ranked, used_ids)
        if alt:
            used_ids.add(alt.resource.id)
        minutes = res.duration_minutes or 240
        hours = round(minutes / 60.0, 1)
        weeks = round(max(hours / hours_per_week, 0.5), 1)
        skill_names = [taxonomy.get_skill(s).name if taxonomy.get_skill(s) else s
                       for s in (stage_skills or res.skills_taught)]

        stages.append(LearningStage(
            stage=i,
            title=res.title,
            outcome=f"Be able to apply: {', '.join(skill_names)}." if skill_names else res.title,
            skills=skill_names,
            prerequisites=[taxonomy.get_skill(p).name if taxonomy.get_skill(p) else p
                           for p in prereqs],
            resources=[StageResource(primary=rr, alternative=alt)],
            project=(StageProject(
                title=f"Apply {skill_names[0]}" if skill_names else "Hands-on exercise",
                description="Build a small artifact that demonstrates this stage's skills.",
                acceptance_criteria=[
                    "Public repository with a clear README.",
                    "Runs from documented steps.",
                    "Demonstrates the stage skills in a concrete task.",
                ],
            ) if res.has_projects else None),
            assessment=(StageAssessment(type="project_review", passing_score=80)
                        if res.has_projects else
                        StageAssessment(type="self_check", passing_score=70)),
            estimated_hours=hours,
            estimated_weeks=weeks,
        ))
        covered_so_far |= set(res.skills_taught)
        sources.append({
            "resource_id": res.id,
            "title": res.title,
            "provider": res.provider,
            "url": res.url,
            "source_type": res.provenance.source_type,
            "last_verified_at": res.provenance.last_verified_at,
        })

    # Portfolio capstone — learn, build, ship. A path that only lists courses is
    # incomplete: the strongest signal is real, published work (spec section 2).
    if stages and getattr(goal, "type", "") in ("career_transition", "topic_mastery"):
        cap_skills = [s.name for sid in gap.missing_skill_ids
                      if (s := taxonomy.get_skill(sid))][:4]
        stages.append(LearningStage(
            stage=len(stages) + 1,
            title="Build & ship a portfolio project",
            outcome="Prove the skills with one real, published project.",
            skills=cap_skills,
            resources=[],
            project=StageProject(
                title=f"Ship a {goal.title} portfolio project",
                description="Combine the skills from earlier stages into one end-to-end "
                            "project you publish and can talk through in an interview.",
                acceptance_criteria=[
                    "Public repository with a clear README",
                    "A live demo or a short recorded walkthrough",
                    "Exercises the core skills from this path",
                ],
            ),
            assessment=StageAssessment(type="project_review", passing_score=80),
            estimated_hours=round(hours_per_week * 2, 1),
            estimated_weeks=2.0,
        ))

    total_hours = sum(s.estimated_hours for s in stages)
    estimated_weeks = round(max(total_hours / hours_per_week, len(stages) * 0.5), 1)

    return LearningPath(
        path_id=path_id,
        resolved_goal=goal,
        duration=PathDuration(estimated_weeks=estimated_weeks, hours_per_week=hours_per_week),
        stages=stages,
        sources=sources,
        uncovered_skills=[taxonomy.get_skill(s).name if taxonomy.get_skill(s) else s
                          for s in uncovered],
    )
