"""Certification definitions — a separate domain, not another topic label.

For vendors without an approved catalog API, Scout uses *manually reviewed*
definitions with an explicit ``last_verified_at`` (spec section 7). Domains carry
official exam weightings so the path optimizer can schedule study time in
proportion to the exam blueprint. Phase 2 will supplement this with the
Credential Engine Registry and the Microsoft Learn Platform API.
"""
from __future__ import annotations

from functools import lru_cache

from app.services.learning.schemas import Certification

_CERTIFICATIONS: list[dict] = [
    {
        # Exam code / version are intentionally null — Scout never invents them
        # (trust rule 3). Domains are framed as recommended study areas mapped to
        # real Claude skill areas, verified against Anthropic's public materials.
        "id": "cert:claude-architect",
        "name": "Anthropic Claude Certified Architect",
        "issuer": "Anthropic",
        "official_url": "https://www.anthropic.com/learn",
        "exam_code": None,
        "version": None,
        "status": "active",
        "last_verified_at": "2026-08-07T00:00:00+00:00",
        "validity": {"expires": False, "duration_months": None},
        "domains": [
            {"name": "Build with the Claude API", "weight": 25,
             "skills": ["skill:claude-api", "skill:prompt-design"]},
            {"name": "Agentic systems: Claude Code & MCP", "weight": 25,
             "skills": ["skill:claude-code", "skill:mcp", "skill:agents"]},
            {"name": "Production applications (RAG & deployment)", "weight": 30,
             "skills": ["skill:rag-foundations", "skill:ai-deployment"]},
            {"name": "Responsible & safe deployment", "weight": 20,
             "skills": ["skill:ai-safety"]},
        ],
    },
    {
        "id": "cert:aws-saa",
        "name": "AWS Certified Solutions Architect – Associate",
        "issuer": "Amazon Web Services",
        "official_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
        "exam_code": "SAA-C03",
        "version": "C03",
        "status": "active",
        "last_verified_at": "2026-01-15T00:00:00+00:00",
        "validity": {"expires": True, "duration_months": 36},
        "domains": [
            {"name": "Design secure architectures", "weight": 30,
             "skills": ["skill:iam", "skill:encryption", "skill:network-security"]},
            {"name": "Design resilient architectures", "weight": 26,
             "skills": ["skill:cloud-foundations", "skill:databases"]},
            {"name": "Design high-performing architectures", "weight": 24,
             "skills": ["skill:cloud-foundations", "skill:databases"]},
            {"name": "Design cost-optimized architectures", "weight": 20,
             "skills": ["skill:cloud-foundations"]},
        ],
    },
    {
        "id": "cert:azure-ai-engineer",
        "name": "Microsoft Certified: Azure AI Engineer Associate",
        "issuer": "Microsoft",
        "official_url": "https://learn.microsoft.com/credentials/certifications/azure-ai-engineer/",
        "exam_code": "AI-102",
        "version": "AI-102",
        "status": "active",
        "last_verified_at": "2026-01-15T00:00:00+00:00",
        "validity": {"expires": True, "duration_months": 12},
        "domains": [
            {"name": "Plan and manage an Azure AI solution", "weight": 25,
             "skills": ["skill:cloud-foundations", "skill:iam", "skill:ai-safety"]},
            {"name": "Implement generative AI solutions", "weight": 25,
             "skills": ["skill:llm-apis", "skill:prompt-design", "skill:ai-safety"]},
            {"name": "Implement knowledge mining and information extraction", "weight": 20,
             "skills": ["skill:embeddings", "skill:rag-foundations"]},
            {"name": "Implement and monitor AI solutions", "weight": 30,
             "skills": ["skill:ai-deployment", "skill:ai-eval"]},
        ],
    },
]


@lru_cache(maxsize=1)
def _index() -> dict[str, Certification]:
    return {c["id"]: Certification(**c) for c in _CERTIFICATIONS}


def all_certifications() -> list[Certification]:
    return list(_index().values())


def get_certification(cert_id: str) -> Certification | None:
    return _index().get(cert_id)


def resolve_certification(name_or_id: str) -> Certification | None:
    if not name_or_id:
        return None
    key = name_or_id.strip().lower()
    for c in _index().values():
        if key == c.id.lower() or key == c.name.lower() or key == (c.exam_code or "").lower():
            return c
    # loose match on name / code
    for c in _index().values():
        hay = " ".join([c.name, c.exam_code or "", c.issuer]).lower()
        if key and all(w in hay for w in key.split()):
            return c
    for c in _index().values():
        if key and key in c.name.lower():
            return c
    return None


def search_certifications(query: str, limit: int = 10) -> list[Certification]:
    q = (query or "").strip().lower()
    if not q:
        return all_certifications()[:limit]
    out = [c for c in _index().values()
           if q in " ".join([c.name, c.issuer, c.exam_code or ""]).lower()]
    return out[:limit]
