"""Certification prep-track builder.

Strong candidates don't prepare for a certification by jumping between random
tutorials — they follow a *typed sequence*: official training, then building
along, then the reference "pillars", then the official exam guide, then practice
questions, then community, then real projects, then registration.

This module turns Scout's evidence-backed, cert-aligned resources into exactly
that ordered track (spec section 7), so certification mode produces a genuinely
useful study plan rather than a flat set-cover of courses. It is deterministic;
the plan narrator only describes it.
"""
from __future__ import annotations

from app.providers import base as providers
from app.providers.static_catalog import StaticCatalogProvider
from app.services.learning import course_ranker, taxonomy
from app.services.learning.schemas import (
    Certification,
    GoalCandidate,
    LearningGoalRequest,
    LearningPath,
    LearningStage,
    PathDuration,
    RankedResource,
    ResourceQuery,
    SkillGap,
    StageAssessment,
    StageProject,
    StageResource,
)

# Canonical phases: (key, resource_types, title, outcome, needs_project, assessment).
_PHASES: list[tuple[str, tuple[str, ...], str, str]] = [
    ("foundations", ("course", "video", "path"),
     "Start with the official training",
     "Understand the fundamentals from authoritative, hands-off material."),
    ("build", ("project", "lab"),
     "Build along with real code",
     "Reading gets you part of the way; building gets you the rest."),
    ("pillars", ("docs",),
     "Go deep on the reference pillars",
     "Work through the authoritative documentation the exam is built on."),
    ("exam_guide", ("exam_guide",),
     "Study the official exam guide",
     "Learn the blueprint and review sample questions with rationale."),
    ("practice", ("practice_exam",),
     "Test yourself with practice questions",
     "Find and close your weak spots before exam day."),
    ("community", ("community",),
     "Join the community",
     "Get access to peers, partners and up-to-date guidance."),
]


def _names(skill_ids: list[str]) -> list[str]:
    out = []
    for sid in skill_ids:
        node = taxonomy.get_skill(sid)
        if node:
            out.append(node.name)
    return out


def _gather(cert: Certification, gap: SkillGap, req: LearningGoalRequest) -> list[RankedResource]:
    """All resources aligned to the cert, plus resources covering its domain
    skills, ranked in certification mode so each card carries reasons/warnings."""
    by_id: dict[str, object] = {}
    for r in StaticCatalogProvider().search(ResourceQuery(limit=300)):
        if cert.id in r.certification_alignment:
            by_id[r.id] = r
    # Also pull resources that cover the cert's domain skills *and their missing
    # prerequisites*, so the foundations phase can fill gaps the learner lacks.
    wanted = list(set(cert.skills()) | set(gap.missing_skill_ids))
    for r in providers.search_all(ResourceQuery(skills=wanted, text=cert.name, limit=150)):
        by_id.setdefault(r.id, r)
    ranked = course_ranker.rank(list(by_id.values()), gap, req, mode="certification")
    return ranked


def build_cert_path(
    path_id: str,
    goal: GoalCandidate,
    gap: SkillGap,
    req: LearningGoalRequest,
    cert: Certification,
) -> LearningPath:
    ranked = _gather(cert, gap, req)
    # Bucket by resource type, best-scored first within each bucket.
    buckets: dict[str, list[RankedResource]] = {}
    for rr in ranked:
        buckets.setdefault(rr.resource.resource_type, []).append(rr)

    hours_per_week = max(1.0, float(req.hours_per_week or 8))
    stages: list[LearningStage] = []
    sources: list[dict] = []
    taught: set[str] = set(gap.known_skill_ids)
    n = 0

    def _add_sources(items: list[RankedResource]) -> None:
        for rr in items:
            res = rr.resource
            sources.append({"resource_id": res.id, "title": res.title, "provider": res.provider,
                            "url": res.url, "source_type": res.provenance.source_type,
                            "last_verified_at": res.provenance.last_verified_at})
            taught.update(res.skills_taught)

    for key, types, title, outcome in _PHASES:
        items: list[RankedResource] = []
        for t in types:
            items.extend(buckets.get(t, []))
        if not items:
            continue
        n += 1
        skills = sorted({s for rr in items for s in rr.resource.skills_taught})
        minutes = sum(rr.resource.duration_minutes or 0 for rr in items)
        hours = round(minutes / 60.0, 1)
        stages.append(LearningStage(
            stage=n, title=title, outcome=outcome,
            skills=_names(skills),
            resources=[StageResource(primary=rr) for rr in items],
            project=(StageProject(
                title="Build along and keep the code",
                description="Reproduce the examples and adapt one to your own use case.",
                acceptance_criteria=["Public repository", "Runs from documented steps",
                                     "One original adaptation"],
            ) if key == "build" else None),
            assessment=(StageAssessment(type="practice_exam", passing_score=80)
                        if key in ("exam_guide", "practice") else None),
            estimated_hours=hours,
            estimated_weeks=round(max(hours / hours_per_week, 0.5), 1),
        ))
        _add_sources(items)

    # Portfolio capstone — the differentiator: a certification proves credibility,
    # a portfolio proves capability. Always included.
    n += 1
    stages.append(LearningStage(
        stage=n, title="Build 3 real projects",
        outcome="Demonstrate what you can actually build with the skills you've learned.",
        skills=_names(gap.missing_skill_ids)[:4],
        resources=[],
        project=StageProject(
            title="Ship three portfolio projects",
            description="Learn, build, practice, ship, repeat. Publish three real projects "
                        "that exercise the exam's core skills end to end.",
            acceptance_criteria=[
                "Three public repositories, each with a clear README and a live demo or recording",
                "Together they cover the certification's main domains",
                "At least one uses an agent / tool-use pattern",
            ],
        ),
        assessment=StageAssessment(type="project_review", passing_score=80),
        estimated_hours=round(hours_per_week * 3, 1),
        estimated_weeks=3.0,
    ))

    # Registration is always the final step.
    reg = buckets.get("registration", [])
    n += 1
    stages.append(LearningStage(
        stage=n, title="Register and take the exam",
        outcome="Book the exam once your practice scores are consistently above the bar.",
        skills=[],
        resources=[StageResource(primary=rr) for rr in reg],
        project=None,
        assessment=None,
        estimated_hours=0.5, estimated_weeks=0.5,
    ))
    _add_sources(reg)

    total_hours = sum(s.estimated_hours for s in stages)
    weeks = round(max(total_hours / hours_per_week, len(stages) * 0.5), 1)
    uncovered = [taxonomy.get_skill(s).name for s in gap.missing_skill_ids
                 if s not in taught and taxonomy.get_skill(s)]

    return LearningPath(
        path_id=path_id,
        resolved_goal=goal,
        duration=PathDuration(estimated_weeks=weeks, hours_per_week=hours_per_week),
        stages=stages,
        sources=sources,
        uncovered_skills=uncovered,
    )
