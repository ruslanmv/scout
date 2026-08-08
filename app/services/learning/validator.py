"""Path validator — reject unsupported facts and invalid sequences.

The optimizer is deterministic, but AI narration and future live data could
introduce claims Scout must not make. The validator enforces the trust rules
(spec section 17): every cited resource must have provenance and a URL,
prerequisites must precede dependents, and unverifiable price/rating claims must
be labelled rather than asserted.
"""
from __future__ import annotations

from app.services.learning.schemas import LearningPath


def validate(path: LearningPath) -> tuple[bool, list[str]]:
    """Return ``(ok, warnings)``. ``ok`` is False only for hard violations."""
    from app.services.learning import taxonomy

    warnings: list[str] = list(path.warnings)
    hard_error = False

    # Map the topological position of every skill taught, by skill id, so we can
    # verify graph prerequisites are never scheduled after their dependents.
    stage_of_skill: dict[str, int] = {}
    for stage in path.stages:
        for sr in stage.resources:
            for sid in sr.primary.resource.skills_taught:
                stage_of_skill.setdefault(sid, stage.stage)

    seen_skills: set[str] = set()
    for stage in path.stages:
        # Prerequisite ordering (display level): a stage's declared prerequisites
        # must already have appeared — never later in the path.
        for pre in stage.prerequisites:
            future = any(pre in s.skills for s in path.stages if s.stage > stage.stage)
            if future and pre not in seen_skills:
                warnings.append(
                    f"Stage {stage.stage} depends on '{pre}' which is scheduled later.")
                hard_error = True
        seen_skills.update(stage.skills)

        # Prerequisite ordering (graph level): for each skill this stage teaches,
        # none of its graph prerequisites may be taught in a *later* stage.
        for sr in stage.resources:
            for sid in sr.primary.resource.skills_taught:
                node = taxonomy.get_skill(sid)
                if not node:
                    continue
                for pre in node.prerequisites:
                    pre_stage = stage_of_skill.get(pre)
                    if pre_stage is not None and pre_stage > stage.stage:
                        pre_name = (taxonomy.get_skill(pre).name
                                    if taxonomy.get_skill(pre) else pre)
                        warnings.append(
                            f"Stage {stage.stage} teaches a skill whose prerequisite "
                            f"'{pre_name}' is scheduled later (stage {pre_stage}).")
                        hard_error = True

        for sr in stage.resources:
            res = sr.primary.resource
            if not res.url:
                warnings.append(f"Stage {stage.stage} resource '{res.title}' has no URL.")
                hard_error = True
            if res.provenance.source_type is None:
                warnings.append(f"Stage {stage.stage} resource '{res.title}' has no provenance.")
                hard_error = True
            # Never assert a free/price claim we did not observe.
            if res.access.type in {"free", "free_audit"} and res.access.observed_at is None:
                warnings.append(
                    f"'{res.title}' claims free access without a recent observation.")
                hard_error = True

    if path.uncovered_skills:
        warnings.append(
            "Some required skills are not covered by any found resource: "
            + ", ".join(path.uncovered_skills))

    # Deduplicate while preserving order.
    deduped: list[str] = []
    for w in warnings:
        if w not in deduped:
            deduped.append(w)
    return (not hard_error), deduped
