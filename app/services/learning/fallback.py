"""Deterministic fallback path.

Produces a useful, honest path directly from the skill gap when resource search
returns nothing usable (no providers, everything filtered out). Stages list the
skills to learn in prerequisite order and point at the internal skill graph,
without inventing courses, prices or ratings (spec sections 11, 13, 17).
"""
from __future__ import annotations

from app.services.learning import taxonomy
from app.services.learning.schemas import (
    GoalCandidate,
    LearningGoalRequest,
    LearningPath,
    LearningStage,
    PathDuration,
    PathRationale,
    SkillGap,
    StageAssessment,
    StageProject,
)


def build_fallback_path(
    path_id: str,
    goal: GoalCandidate,
    gap: SkillGap,
    req: LearningGoalRequest,
) -> LearningPath:
    hours_per_week = max(1.0, float(req.hours_per_week or 8))
    stages: list[LearningStage] = []
    for i, sid in enumerate(gap.missing_skill_ids, start=1):
        node = taxonomy.get_skill(sid)
        if node is None:
            continue
        prereq_names = [taxonomy.get_skill(p).name for p in node.prerequisites
                        if taxonomy.get_skill(p)]
        est_hours = 8.0
        stages.append(LearningStage(
            stage=i,
            title=f"Learn {node.name}",
            outcome=f"Be able to apply {node.name}.",
            skills=[node.name],
            prerequisites=prereq_names,
            resources=[],
            project=StageProject(
                title=f"Practice {node.name}",
                description="Build a small artifact that demonstrates this skill.",
                acceptance_criteria=["Public repository", "Documented steps"],
            ),
            assessment=StageAssessment(type="self_check", passing_score=70),
            estimated_hours=est_hours,
            estimated_weeks=round(max(est_hours / hours_per_week, 0.5), 1),
        ))

    total_hours = sum(s.estimated_hours for s in stages)
    weeks = round(max(total_hours / hours_per_week, len(stages) * 0.5), 1)
    return LearningPath(
        path_id=path_id,
        resolved_goal=goal,
        rationale=PathRationale(
            summary=(f"Live course discovery was unavailable, so this is Scout's "
                     f"deterministic skill-ordered plan toward {goal.title}. Each "
                     f"stage names a skill to master in prerequisite order."),
            confidence=0.4,
        ),
        duration=PathDuration(estimated_weeks=weeks, hours_per_week=hours_per_week),
        stages=stages,
        warnings=["No verified course resources were available; showing a skill-only path."],
        uncovered_skills=[taxonomy.get_skill(s).name for s in gap.missing_skill_ids
                          if taxonomy.get_skill(s)],
        source="deterministic-fallback",
    )
