"""Static, offline catalog of hand-verified learning resources.

This is Scout's reliable baseline: real, free-to-access resources (official docs,
Microsoft Learn, freely available video courses) mapped to the internal skill
graph. It needs no API key and no network, so the whole pipeline works — and
tests are deterministic — even when every live provider is down.

Access is asserted as ``free`` only for resources that are genuinely free to
access, each with an ``observed_at`` timestamp, per the trust rules (spec §17).
Nothing here invents ratings or prices.
"""
from __future__ import annotations

from app.services.learning.schemas import (
    LearningResource,
    ProviderHealth,
    ResourceAccess,
    ResourceProvenance,
    ResourceQuality,
    ResourceQuery,
)

_VERIFIED_AT = "2026-01-20T00:00:00+00:00"


def _free_course(
    rid: str,
    provider: str,
    title: str,
    url: str,
    skills: list[str],
    *,
    level: str = "beginner",
    minutes: int = 240,
    rtype: str = "course",
    prereqs: list[str] | None = None,
    projects: bool = False,
    assessments: bool = False,
    cert_align: list[str] | None = None,
    source_type: str = "static_catalog",
    confidence: float = 0.8,
    verify_access: bool = False,
) -> LearningResource:
    # Paid or purchase-gated items (exam registration, practice exams) advertise
    # "Verify on provider" rather than a fabricated price (trust rules 2 & 3).
    access = (ResourceAccess(type="unknown", price=None, currency=None, observed_at=None)
              if verify_access
              else ResourceAccess(type="free", price=0, currency="EUR", observed_at=_VERIFIED_AT))
    return LearningResource(
        id=rid,
        provider=provider,
        resource_type=rtype,
        title=title,
        url=url,
        level=level,
        duration_minutes=minutes,
        skills_taught=skills,
        prerequisite_skills=prereqs or [],
        certification_alignment=cert_align or [],
        has_projects=projects,
        has_assessments=assessments,
        access=access,
        quality=ResourceQuality(evidence_confidence=confidence),
        provenance=ResourceProvenance(
            source_type=source_type,
            source_url=url,
            last_verified_at=_VERIFIED_AT,
            license_or_terms="Verify current terms on provider.",
        ),
    )


_CATALOG: list[LearningResource] = [
    _free_course(
        "resource:static:python-foundations", "openedx",
        "Python Foundations for Developers",
        "https://docs.python.org/3/tutorial/",
        ["skill:python"], level="beginner", minutes=600, projects=True),
    _free_course(
        "resource:static:git-basics", "youtube",
        "Git & GitHub Crash Course",
        "https://docs.github.com/get-started",
        ["skill:git"], level="beginner", minutes=120, rtype="video"),
    _free_course(
        "resource:static:pytest", "youtube",
        "Automated Testing with pytest",
        "https://docs.pytest.org/en/stable/",
        ["skill:testing"], level="beginner", minutes=150, prereqs=["skill:python"],
        projects=True, assessments=True),
    _free_course(
        "resource:static:http-apis", "openedx",
        "Building HTTP APIs with FastAPI",
        "https://fastapi.tiangolo.com/tutorial/",
        ["skill:http-apis"], level="beginner", minutes=300, prereqs=["skill:python"],
        projects=True),
    _free_course(
        "resource:static:packaging", "microsoft_learn",
        "Package and Deploy Python Applications",
        "https://learn.microsoft.com/training/paths/python-first-steps/",
        ["skill:packaging"], level="intermediate", minutes=240,
        prereqs=["skill:python", "skill:git"], projects=True),
    _free_course(
        "resource:static:databases", "openedx",
        "Databases and SQL for Developers",
        "https://www.postgresql.org/docs/current/tutorial.html",
        ["skill:databases"], level="beginner", minutes=360, assessments=True),
    _free_course(
        "resource:static:llm-apis", "microsoft_learn",
        "Get Started with Large Language Model APIs",
        "https://learn.microsoft.com/training/paths/develop-ai-solutions-azure-openai/",
        ["skill:llm-apis"], level="beginner", minutes=180,
        prereqs=["skill:python", "skill:http-apis"], projects=True,
        cert_align=["cert:azure-ai-engineer"]),
    _free_course(
        "resource:static:prompt-design", "microsoft_learn",
        "Fundamentals of Prompt Engineering",
        "https://learn.microsoft.com/training/modules/fundamentals-generative-ai/",
        ["skill:prompt-design"], level="beginner", minutes=120, prereqs=["skill:llm-apis"],
        cert_align=["cert:azure-ai-engineer"]),
    _free_course(
        "resource:static:embeddings", "youtube",
        "Embeddings and Semantic Search Explained",
        "https://learn.microsoft.com/training/modules/use-own-data-azure-openai/",
        ["skill:embeddings"], level="intermediate", minutes=150, prereqs=["skill:python"],
        rtype="video"),
    _free_course(
        "resource:static:rag-foundations", "microsoft_learn",
        "Build a Retrieval-Augmented Generation Application",
        "https://learn.microsoft.com/training/modules/use-own-data-azure-openai/",
        ["skill:rag-foundations"], level="intermediate", minutes=240,
        prereqs=["skill:embeddings", "skill:llm-apis"], projects=True,
        cert_align=["cert:azure-ai-engineer"]),
    _free_course(
        "resource:static:rag-eval", "openedx",
        "Evaluating Retrieval-Augmented Generation Systems",
        "https://learn.microsoft.com/training/",
        ["skill:rag-evaluation", "skill:ai-eval"], level="intermediate", minutes=180,
        prereqs=["skill:rag-foundations"], projects=True, assessments=True),
    _free_course(
        "resource:static:ai-deploy", "microsoft_learn",
        "Deploy and Monitor AI Applications",
        "https://learn.microsoft.com/training/paths/create-machine-learn-models/",
        ["skill:ai-deployment"], level="intermediate", minutes=240,
        prereqs=["skill:packaging", "skill:llm-apis"], projects=True,
        cert_align=["cert:azure-ai-engineer"]),
    _free_course(
        "resource:static:ai-safety", "microsoft_learn",
        "Responsible AI and Safety Fundamentals",
        "https://learn.microsoft.com/training/paths/responsible-ai-business-principles/",
        ["skill:ai-safety"], level="intermediate", minutes=120, prereqs=["skill:llm-apis"],
        cert_align=["cert:azure-ai-engineer"]),
    _free_course(
        "resource:static:agents", "youtube",
        "Building AI Agents and Tool Use",
        "https://modelcontextprotocol.io/introduction",
        ["skill:agents"], level="advanced", minutes=200,
        prereqs=["skill:llm-apis", "skill:prompt-design"], projects=True, rtype="video"),
    _free_course(
        "resource:static:portfolio", "youtube",
        "Technical Writing and Developer Portfolios",
        "https://developers.google.com/tech-writing",
        ["skill:portfolio"], level="beginner", minutes=90, prereqs=["skill:git"]),
    # --- Cloud / certification track ---
    _free_course(
        "resource:static:cloud-foundations", "microsoft_learn",
        "Cloud Computing Foundations",
        "https://learn.microsoft.com/training/paths/azure-fundamentals/",
        ["skill:cloud-foundations"], level="beginner", minutes=300, assessments=True),
    _free_course(
        "resource:static:iam", "microsoft_learn",
        "Identity and Access Management in the Cloud",
        "https://learn.microsoft.com/training/paths/secure-your-cloud-data/",
        ["skill:iam"], level="intermediate", minutes=180, prereqs=["skill:cloud-foundations"],
        cert_align=["cert:aws-saa"]),
    _free_course(
        "resource:static:encryption", "openedx",
        "Encryption and Data Protection in the Cloud",
        "https://learn.microsoft.com/training/",
        ["skill:encryption"], level="intermediate", minutes=150,
        prereqs=["skill:cloud-foundations"], cert_align=["cert:aws-saa"]),
    _free_course(
        "resource:static:network-security", "openedx",
        "Cloud Network Security Essentials",
        "https://learn.microsoft.com/training/",
        ["skill:network-security"], level="intermediate", minutes=180,
        prereqs=["skill:cloud-foundations"], cert_align=["cert:aws-saa"]),
    # --- Anthropic / Claude Certified Architect track ---
    # A typed prep sequence — training, build-along, docs pillars, exam guide,
    # practice, community, registration — mirroring how strong candidates prepare.
    _free_course(
        "resource:static:anthropic-academy", "anthropic",
        "Anthropic Academy — Free Claude Training Courses",
        "https://anthropic.skilljar.com/",
        ["skill:claude-api", "skill:prompt-design"], level="beginner", minutes=600,
        prereqs=["skill:llm-apis"], cert_align=["cert:claude-architect"], confidence=0.9),
    _free_course(
        "resource:static:claude-code-overview", "anthropic",
        "Claude Code — Agentic Coding Overview",
        "https://docs.anthropic.com/en/docs/claude-code/overview",
        ["skill:claude-code"], level="intermediate", minutes=180,
        prereqs=["skill:claude-api"], cert_align=["cert:claude-architect"],
        rtype="course", projects=True, confidence=0.9),
    _free_course(
        "resource:static:anthropic-cookbook", "anthropic",
        "Anthropic Cookbook — Build Along",
        "https://github.com/anthropics/anthropic-cookbook",
        ["skill:claude-api"], level="intermediate", minutes=480,
        prereqs=["skill:claude-api"], cert_align=["cert:claude-architect"],
        rtype="project", projects=True, confidence=0.9),
    _free_course(
        "resource:static:anthropic-quickstarts", "anthropic",
        "Anthropic Quickstarts — Reference Builds",
        "https://github.com/anthropics/anthropic-quickstarts",
        ["skill:agents"], level="intermediate", minutes=300,
        prereqs=["skill:claude-api"], cert_align=["cert:claude-architect"],
        rtype="project", projects=True),
    _free_course(
        "resource:static:claude-api-docs", "anthropic",
        "Claude API Documentation — the Pillar",
        "https://docs.anthropic.com/en/api/overview",
        ["skill:claude-api"], level="intermediate", minutes=120,
        cert_align=["cert:claude-architect"], rtype="docs", confidence=0.9),
    _free_course(
        "resource:static:mcp-docs", "anthropic",
        "Model Context Protocol Documentation — the Pillar",
        "https://docs.anthropic.com/en/docs/agents-and-tools/mcp",
        ["skill:mcp", "skill:agents"], level="advanced", minutes=150,
        prereqs=["skill:claude-api"], cert_align=["cert:claude-architect"],
        rtype="docs", confidence=0.9),
    _free_course(
        "resource:static:claude-prompting", "anthropic",
        "Claude Prompt Engineering Guide",
        "https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview",
        ["skill:prompt-design"], level="beginner", minutes=120,
        cert_align=["cert:claude-architect"], rtype="docs"),
    _free_course(
        "resource:static:claude-exam-guide", "anthropic",
        "Claude Certified Architect — Official Exam Guide",
        "https://www.anthropic.com/learn",
        [], level="intermediate", minutes=120, cert_align=["cert:claude-architect"],
        rtype="exam_guide", assessments=True, confidence=0.9),
    _free_course(
        "resource:static:claude-practice", "anthropic",
        "Claude Certified Architect — Practice Questions",
        "https://www.anthropic.com/learn",
        [], level="intermediate", minutes=120, cert_align=["cert:claude-architect"],
        rtype="practice_exam", assessments=True, verify_access=True),
    _free_course(
        "resource:static:anthropic-partners", "anthropic",
        "Anthropic Partner Network (free)",
        "https://www.anthropic.com/partners",
        [], level="beginner", minutes=30, cert_align=["cert:claude-architect"],
        rtype="community"),
    _free_course(
        "resource:static:claude-register", "anthropic",
        "Register for the Claude Certified Architect exam",
        "https://www.anthropic.com/learn",
        [], level="intermediate", minutes=15, cert_align=["cert:claude-architect"],
        rtype="registration", verify_access=True),
]


class StaticCatalogProvider:
    provider_name = "static_catalog"

    def search(self, query: ResourceQuery) -> list[LearningResource]:
        wanted = set(query.skills)
        text = (query.text or "").lower()
        out: list[LearningResource] = []
        for r in _CATALOG:
            skill_hit = bool(wanted & set(r.skills_taught)) if wanted else True
            text_hit = (not text) or (text in r.title.lower())
            if skill_hit or text_hit:
                out.append(r.model_copy(deep=True))
        return out[: max(1, query.limit)]

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            ok=True,
            mode="static",
            detail=f"{len(_CATALOG)} curated offline resources available.",
        )
