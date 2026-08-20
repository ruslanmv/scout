"""Pydantic models for Scout's Learning Navigator.

These describe the full deterministic pipeline contract:

    request -> resolved goal -> skill gap -> resources -> ranking -> path

Every model is intentionally explicit about *provenance* and *access*, because
Scout's core rule is that recommendations must be evidence-backed and never
invent prices, ratings, or certification facts (see TRUST.md and the product
spec, section 17). AI only narrates a path that deterministic logic produced.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

# --- Enumerations -----------------------------------------------------------

Intent = Literal[
    "learn_topic",
    "prepare_certification",
    "advance_career",
    "discover_next",
]

SkillLevel = Literal["beginner", "intermediate", "advanced", "unknown"]

ResourceType = Literal[
    "course",
    "path",
    "video",
    "playlist",
    "article",
    "docs",          # authoritative reference documentation ("the pillars")
    "lab",
    "project",       # build-along / hands-on repository
    "practice_exam",
    "exam_guide",     # official exam blueprint + sample questions
    "community",      # partner network / forum / peer group
    "registration",   # register for / schedule the exam
    "certification",
]

# Access is never a permanent boolean. It is an *observation* with a timestamp.
AccessType = Literal[
    "free",
    "free_audit",
    "free_preview",
    "free_trial",
    "subscription",
    "paid",
    "unknown",
]

SourceType = Literal[
    "official_api",
    "structured_catalog",
    "web_search",
    "static_catalog",
    "manual_review",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Learner input ----------------------------------------------------------

class SkillRef(BaseModel):
    name: str
    level: SkillLevel = "unknown"


class Budget(BaseModel):
    maximum: float | None = None
    currency: str = "EUR"
    free_only: bool = False


class LearningPreferences(BaseModel):
    video: bool = True
    reading: bool = True
    projects: bool = True
    interactive_labs: bool = True


class CredentialGoal(BaseModel):
    required: bool = False
    type: str | None = None


class LearningGoalRequest(BaseModel):
    """Rich replacement for the legacy ``/ai/plan`` request (spec section 3)."""

    intent: Intent = "learn_topic"
    query: str = ""
    target_role: str | None = None
    target_certification: str | None = None
    current_role: str | None = None
    current_skills: list[SkillRef] = Field(default_factory=list)
    experience_years: float | None = None
    country: str | None = None
    city: str | None = None
    use_location: bool = True
    language: str = "English"
    hours_per_week: float = 8
    target_date: str | None = None
    budget: Budget = Field(default_factory=Budget)
    preferred_providers: list[str] = Field(default_factory=list)
    learning_preferences: LearningPreferences = Field(default_factory=LearningPreferences)
    credential_goal: CredentialGoal = Field(default_factory=CredentialGoal)


# --- Skills & occupations ---------------------------------------------------

class SkillNode(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    level: SkillLevel = "intermediate"
    prerequisites: list[str] = Field(default_factory=list)
    related_occupations: list[str] = Field(default_factory=list)
    durability: float = 0.6  # 0..1 — how slowly the skill goes stale
    external_ids: dict[str, str] = Field(default_factory=dict)


class Occupation(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    domain: str = ""  # ESCO-major-group domain (Scout 2.0); see taxonomy.DOMAINS
    core_skills: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)


# --- Certifications ---------------------------------------------------------

class CertificationDomain(BaseModel):
    name: str
    weight: float = 0
    skills: list[str] = Field(default_factory=list)


class CertificationValidity(BaseModel):
    expires: bool = False
    duration_months: int | None = None


class Certification(BaseModel):
    id: str
    name: str
    issuer: str
    official_url: str = ""
    exam_code: str | None = None
    version: str | None = None
    status: str = "active"
    domains: list[CertificationDomain] = Field(default_factory=list)
    validity: CertificationValidity = Field(default_factory=CertificationValidity)
    last_verified_at: str | None = None

    def skills(self) -> list[str]:
        seen: list[str] = []
        for d in self.domains:
            for s in d.skills:
                if s not in seen:
                    seen.append(s)
        return seen


# --- Normalized learning resource (spec section 9) --------------------------

class ResourceAccess(BaseModel):
    type: AccessType = "unknown"
    price: float | None = None
    currency: str | None = None
    observed_at: str | None = None


class ResourceQuality(BaseModel):
    rating: float | None = None
    rating_count: int | None = None
    evidence_confidence: float = 0.5


class ResourceProvenance(BaseModel):
    source_type: SourceType = "static_catalog"
    source_url: str = ""
    retrieved_at: str = Field(default_factory=now_iso)
    last_verified_at: str | None = None
    license_or_terms: str | None = None
    content_hash: str | None = None
    parser_version: str = "learning-v1"


class LearningResource(BaseModel):
    id: str
    provider: str
    resource_type: ResourceType = "course"
    title: str
    description: str = ""
    url: str = ""
    instructors: list[str] = Field(default_factory=list)
    language: str = "en"
    level: SkillLevel = "unknown"
    duration_minutes: int | None = None
    skills_taught: list[str] = Field(default_factory=list)
    prerequisite_skills: list[str] = Field(default_factory=list)
    certification_alignment: list[str] = Field(default_factory=list)
    has_projects: bool = False
    has_assessments: bool = False
    access: ResourceAccess = Field(default_factory=ResourceAccess)
    quality: ResourceQuality = Field(default_factory=ResourceQuality)
    provenance: ResourceProvenance = Field(default_factory=ResourceProvenance)

    def price_display(self) -> str:
        """Never assert a price we didn't recently observe (spec section 17)."""
        if self.access.type in {"free", "free_audit"} and self.access.observed_at:
            return "Free"
        if self.access.price is not None and self.access.observed_at:
            return f"{self.access.price:.0f} {self.access.currency or ''}".strip()
        return "Verify on provider"


# --- Provider plumbing ------------------------------------------------------

class ResourceQuery(BaseModel):
    text: str = ""
    skills: list[str] = Field(default_factory=list)
    language: str = "en"
    level: SkillLevel | None = None
    providers: list[str] = Field(default_factory=list)
    free_only: bool = False
    limit: int = 20


class ProviderHealth(BaseModel):
    provider: str
    ok: bool
    mode: str = "unknown"  # e.g. "structured", "search", "static", "disabled"
    detail: str = ""
    checked_at: str = Field(default_factory=now_iso)


# --- Goal resolution --------------------------------------------------------

GoalType = Literal["topic_mastery", "certification", "career_transition", "next_topic"]


class GoalCandidate(BaseModel):
    id: str
    title: str
    type: GoalType = "topic_mastery"
    reason: str = ""
    target_role: str | None = None
    target_certification: str | None = None
    skills: list[str] = Field(default_factory=list)


class ResolvedGoal(BaseModel):
    id: str
    query: str = ""
    intent: Intent = "learn_topic"
    recommended: GoalCandidate
    alternatives: list[GoalCandidate] = Field(default_factory=list)
    location_effect: str | None = None
    generated_at: str = Field(default_factory=now_iso)


# --- Skill gap --------------------------------------------------------------

class SkillGapItem(BaseModel):
    skill_id: str
    name: str
    level: SkillLevel = "intermediate"
    priority: float = 0.0
    already_known: bool = False
    reason: str = ""


class SkillGap(BaseModel):
    goal_id: str
    required: list[SkillGapItem] = Field(default_factory=list)
    ordered_skill_ids: list[str] = Field(default_factory=list)  # topological order
    known_skill_ids: list[str] = Field(default_factory=list)
    missing_skill_ids: list[str] = Field(default_factory=list)


# --- Ranking ----------------------------------------------------------------

class RankedResource(BaseModel):
    resource: LearningResource
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# --- Plan / path (spec section 12) ------------------------------------------

class StageProject(BaseModel):
    title: str = ""
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


class StageAssessment(BaseModel):
    type: str = "project_review"
    passing_score: int = 80


class StageResource(BaseModel):
    """A resource attached to a stage, plus a cheaper/free alternative."""

    primary: RankedResource
    alternative: RankedResource | None = None


class LearningStage(BaseModel):
    stage: int
    stage_id: str = ""  # stable id (survives replanning); assigned by the orchestrator
    title: str
    outcome: str = ""
    skills: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    resources: list[StageResource] = Field(default_factory=list)
    project: StageProject | None = None
    assessment: StageAssessment | None = None
    estimated_hours: float = 0
    estimated_weeks: float = 0


class PathRationale(BaseModel):
    summary: str = ""
    location_effect: str | None = None
    confidence: float = 0.6


class PathDuration(BaseModel):
    estimated_weeks: float = 0
    hours_per_week: float = 8


class LearningPath(BaseModel):
    path_id: str
    resolved_goal: GoalCandidate
    rationale: PathRationale = Field(default_factory=PathRationale)
    duration: PathDuration = Field(default_factory=PathDuration)
    stages: list[LearningStage] = Field(default_factory=list)
    alternatives: list[GoalCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    uncovered_skills: list[str] = Field(default_factory=list)
    source: str = "deterministic"  # or the AI provider name once narrated
    generated_at: str = Field(default_factory=now_iso)
    replan_after: dict = Field(default_factory=lambda: {"completed_stages": 1})


# --- Progress ---------------------------------------------------------------

class ProgressEvent(BaseModel):
    path_id: str
    stage: int
    status: Literal["started", "completed", "skipped"] = "completed"
    score: float | None = None
    note: str | None = None
    at: str = Field(default_factory=now_iso)
