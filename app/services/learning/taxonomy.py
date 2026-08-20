"""Seed skill graph, occupations and learning targets.

A learning path is generated from a *directed skill graph*, not from an LLM
prompt (spec section 5). This module is Scout's internal taxonomy — a compact,
hand-curated DAG for the software / AI-engineering domain, with stable ids and
placeholders for external identifiers (ESCO / O*NET / CASE) that Phase 2 will
populate from the real web services.

The graph is deterministic and offline: it is the backbone that keeps the
product reliable when live catalog and AI calls are unavailable.
"""
from __future__ import annotations

from functools import lru_cache

from app.services.learning.schemas import GoalCandidate, Occupation, SkillNode

# --- Skills -----------------------------------------------------------------
# durability: 0..1, how slowly the skill goes stale (fundamentals are durable).

_SKILLS: list[dict] = [
    {"id": "skill:python", "name": "Python", "level": "beginner", "durability": 0.9,
     "aliases": ["python3", "python programming"],
     "description": "General-purpose programming with Python.",
     "external_ids": {"esco": "", "onet": "", "case": ""}},
    {"id": "skill:git", "name": "Git & version control", "level": "beginner", "durability": 0.9,
     "aliases": ["version control", "github workflow"]},
    {"id": "skill:testing", "name": "Automated testing", "level": "beginner", "durability": 0.85,
     "prerequisites": ["skill:python"], "aliases": ["unit testing", "pytest"]},
    {"id": "skill:http-apis", "name": "HTTP APIs", "level": "beginner", "durability": 0.8,
     "prerequisites": ["skill:python"], "aliases": ["rest apis", "web apis"]},
    {"id": "skill:packaging", "name": "Python packaging & deployment", "level": "intermediate",
     "durability": 0.7, "prerequisites": ["skill:python", "skill:git"],
     "aliases": ["packaging", "pip", "docker basics"]},
    {"id": "skill:databases", "name": "Databases & SQL", "level": "beginner", "durability": 0.85,
     "aliases": ["sql", "postgresql"]},
    {"id": "skill:cloud-foundations", "name": "Cloud foundations", "level": "beginner",
     "durability": 0.7, "aliases": ["cloud computing", "aws basics", "azure basics"]},
    {"id": "skill:iam", "name": "Identity & access management", "level": "intermediate",
     "durability": 0.75, "prerequisites": ["skill:cloud-foundations"], "aliases": ["iam"]},
    {"id": "skill:encryption", "name": "Encryption & data protection", "level": "intermediate",
     "durability": 0.8, "prerequisites": ["skill:cloud-foundations"], "aliases": ["kms", "tls"]},
    {"id": "skill:network-security", "name": "Network security", "level": "intermediate",
     "durability": 0.75, "prerequisites": ["skill:cloud-foundations"],
     "aliases": ["vpc", "security groups"]},
    {"id": "skill:llm-apis", "name": "LLM APIs", "level": "beginner", "durability": 0.5,
     "prerequisites": ["skill:python", "skill:http-apis"],
     "aliases": ["openai api", "chat completions", "language model apis"]},
    {"id": "skill:prompt-design", "name": "Prompt design", "level": "beginner", "durability": 0.5,
     "prerequisites": ["skill:llm-apis"], "aliases": ["prompt engineering", "prompting"]},
    {"id": "skill:embeddings", "name": "Embeddings", "level": "intermediate", "durability": 0.6,
     "prerequisites": ["skill:python"], "aliases": ["vector embeddings", "semantic search"]},
    {"id": "skill:rag-foundations", "name": "RAG foundations", "level": "intermediate",
     "durability": 0.55, "prerequisites": ["skill:embeddings", "skill:llm-apis"],
     "aliases": ["retrieval augmented generation", "rag"]},
    {"id": "skill:rag-evaluation", "name": "RAG evaluation", "level": "intermediate",
     "durability": 0.55, "prerequisites": ["skill:python", "skill:embeddings", "skill:rag-foundations"],
     "aliases": ["retrieval evaluation", "rag quality assessment"]},
    {"id": "skill:ai-eval", "name": "LLM evaluation", "level": "intermediate", "durability": 0.55,
     "prerequisites": ["skill:llm-apis"], "aliases": ["model evaluation", "llm testing"]},
    {"id": "skill:ai-deployment", "name": "AI application deployment", "level": "intermediate",
     "durability": 0.6, "prerequisites": ["skill:packaging", "skill:llm-apis"],
     "aliases": ["mlops basics", "serving models"]},
    {"id": "skill:ai-safety", "name": "AI safety & responsible AI", "level": "intermediate",
     "durability": 0.7, "prerequisites": ["skill:llm-apis"],
     "aliases": ["responsible ai", "guardrails"]},
    {"id": "skill:claude-api", "name": "Building with the Claude API", "level": "beginner",
     "durability": 0.5, "prerequisites": ["skill:llm-apis"],
     "aliases": ["claude api", "anthropic api", "messages api"]},
    {"id": "skill:claude-code", "name": "Claude Code & agentic coding", "level": "intermediate",
     "durability": 0.45, "prerequisites": ["skill:git", "skill:claude-api"],
     "aliases": ["claude code", "agentic coding"]},
    {"id": "skill:mcp", "name": "Model Context Protocol (MCP)", "level": "advanced",
     "durability": 0.45, "prerequisites": ["skill:claude-api"],
     "aliases": ["mcp", "model context protocol", "tool servers"]},
    {"id": "skill:agents", "name": "AI agents & tool use", "level": "advanced", "durability": 0.45,
     "prerequisites": ["skill:llm-apis", "skill:prompt-design"],
     "aliases": ["agentic ai", "tool calling"]},
    {"id": "skill:portfolio", "name": "Portfolio & technical writing", "level": "beginner",
     "durability": 0.9, "prerequisites": ["skill:git"],
     "aliases": ["technical writing", "publishing"]},
]


# --- Occupations ------------------------------------------------------------

# --- Domains (Scout 2.0) ----------------------------------------------------
# ~10 domains from the ESCO major occupation groups. The domain selects which
# signal adapters and "Show" playbook apply (see docs/SCOUT_2.0_PLAN.md). Every
# occupation is tagged with exactly one domain so the universal input can group
# and filter across professions, not just software roles.

DOMAINS: list[dict] = [
    {"id": "tech-data", "name": "Tech & Data",
     "description": "Software, data, AI, cloud and IT roles."},
    {"id": "health", "name": "Health",
     "description": "Clinical, nursing, allied-health and care roles."},
    {"id": "business-finance", "name": "Business & Finance",
     "description": "Finance, accounting, operations and management."},
    {"id": "marketing-creative", "name": "Marketing & Creative",
     "description": "Marketing, design, content and communications."},
    {"id": "engineering-manufacturing", "name": "Engineering & Manufacturing",
     "description": "Mechanical, electrical, civil and production engineering."},
    {"id": "education", "name": "Education",
     "description": "Teaching, training and instructional roles."},
    {"id": "legal-public", "name": "Legal & Public",
     "description": "Legal, government and public-administration roles."},
    {"id": "science-research", "name": "Science & Research",
     "description": "Life, physical and social sciences and research."},
    {"id": "trades-logistics", "name": "Trades & Logistics",
     "description": "Skilled trades, construction, transport and logistics."},
    {"id": "hospitality-service", "name": "Hospitality & Service",
     "description": "Hospitality, retail, personal and customer service."},
]


_OCCUPATIONS: list[dict] = [
    {"id": "occupation:ai-engineer", "name": "AI Engineer", "domain": "tech-data",
     "aliases": ["applied ai engineer", "genai engineer", "llm engineer"],
     "description": "Builds and ships applications powered by language models.",
     "core_skills": ["skill:python", "skill:http-apis", "skill:llm-apis", "skill:prompt-design",
                     "skill:embeddings", "skill:rag-foundations", "skill:rag-evaluation",
                     "skill:ai-deployment", "skill:ai-safety", "skill:portfolio"],
     "specializations": ["skill:agents", "skill:ai-eval"],
     "external_ids": {"onet": "15-1299.00", "esco": ""}},
    {"id": "occupation:ml-engineer", "domain": "tech-data", "name": "Machine Learning Engineer",
     "aliases": ["ml engineer"],
     "description": "Trains, evaluates and serves machine-learning models.",
     "core_skills": ["skill:python", "skill:databases", "skill:embeddings", "skill:ai-eval",
                     "skill:ai-deployment", "skill:portfolio"],
     "specializations": ["skill:rag-foundations"]},
    {"id": "occupation:backend-developer", "domain": "tech-data", "name": "Backend Developer",
     "aliases": ["backend engineer", "server developer"],
     "description": "Builds server-side services, APIs and data layers.",
     "core_skills": ["skill:python", "skill:git", "skill:testing", "skill:http-apis",
                     "skill:databases", "skill:packaging"],
     "specializations": ["skill:cloud-foundations"]},
    {"id": "occupation:cloud-architect", "domain": "tech-data", "name": "Cloud Solutions Architect",
     "aliases": ["solutions architect", "cloud engineer"],
     "description": "Designs secure, resilient and cost-effective cloud architectures.",
     "core_skills": ["skill:cloud-foundations", "skill:iam", "skill:encryption",
                     "skill:network-security", "skill:databases"],
     "specializations": []},
    {"id": "occupation:data-analyst", "domain": "tech-data", "name": "Data Analyst",
     "aliases": ["business analyst", "bi analyst", "analytics"],
     "description": "Turns data into decisions with SQL, dashboards and reporting.",
     "core_skills": ["skill:databases", "skill:python"], "specializations": []},
    {"id": "occupation:data-scientist", "domain": "tech-data", "name": "Data Scientist",
     "aliases": ["ml scientist", "statistician"],
     "description": "Builds models and experiments to answer questions with data.",
     "core_skills": ["skill:python", "skill:databases", "skill:embeddings"], "specializations": []},
    # --- Universal input (Scout 2.0 Phase 1): occupations across domains. Non-tech
    # roles are seeded for the typeahead/report; their learning paths stay sparse
    # until Phase 3 adds cross-domain skills and signals.
    {"id": "occupation:registered-nurse", "domain": "health", "name": "Registered Nurse",
     "aliases": ["nurse", "rn", "staff nurse"],
     "description": "Delivers and coordinates patient care in clinical settings."},
    {"id": "occupation:nurse-practitioner", "domain": "health", "name": "Nurse Practitioner",
     "aliases": ["advanced practice nurse", "np"],
     "description": "Advanced-practice nurse who diagnoses and manages care."},
    {"id": "occupation:accountant", "domain": "business-finance", "name": "Accountant",
     "aliases": ["cpa", "bookkeeper", "auditor"],
     "description": "Prepares and reviews financial records and reporting."},
    {"id": "occupation:financial-analyst", "domain": "business-finance", "name": "Financial Analyst",
     "aliases": ["finance analyst", "investment analyst", "fp&a"],
     "description": "Analyzes financial data to guide business and investment decisions."},
    {"id": "occupation:project-manager", "domain": "business-finance", "name": "Project Manager",
     "aliases": ["program manager", "pm", "scrum master"],
     "description": "Plans, coordinates and delivers projects to scope and schedule."},
    {"id": "occupation:marketing-specialist", "domain": "marketing-creative", "name": "Marketing Specialist",
     "aliases": ["marketer", "growth marketer", "digital marketer", "growth hacker"],
     "description": "Plans and runs campaigns across channels to grow demand."},
    {"id": "occupation:ux-designer", "domain": "marketing-creative", "name": "UX/Product Designer",
     "aliases": ["ux designer", "ui designer", "product designer"],
     "description": "Designs usable, useful product experiences."},
    {"id": "occupation:content-writer", "domain": "marketing-creative", "name": "Content Writer",
     "aliases": ["copywriter", "technical writer", "content strategist"],
     "description": "Writes and edits content that informs and converts."},
    {"id": "occupation:mechanical-engineer", "domain": "engineering-manufacturing",
     "name": "Mechanical Engineer", "aliases": ["design engineer", "mechanical designer"],
     "description": "Designs and analyzes mechanical systems and products."},
    {"id": "occupation:electrician", "domain": "trades-logistics", "name": "Electrician",
     "aliases": ["electrical technician", "sparky"],
     "description": "Installs and maintains electrical systems."},
    {"id": "occupation:teacher", "domain": "education", "name": "Teacher",
     "aliases": ["educator", "instructor", "tutor"],
     "description": "Plans and delivers instruction and assesses learning."},
    {"id": "occupation:lawyer", "domain": "legal-public", "name": "Lawyer",
     "aliases": ["attorney", "solicitor", "legal counsel"],
     "description": "Advises on and represents legal matters."},
    {"id": "occupation:research-scientist", "domain": "science-research", "name": "Research Scientist",
     "aliases": ["researcher", "postdoc", "r&d scientist"],
     "description": "Designs and runs studies to advance knowledge."},
    {"id": "occupation:chef", "domain": "hospitality-service", "name": "Chef",
     "aliases": ["cook", "culinary", "kitchen manager"],
     "description": "Plans menus and leads food preparation."},
]


# --- Learning targets (for goal resolution) ---------------------------------
# These map a vague query to one or more concrete, complete targets (spec §2).

_TARGETS: list[dict] = [
    {"id": "target:applied-genai", "title": "Applied Generative AI Engineering",
     "type": "career_transition", "target_role": "AI Engineer",
     "keywords": ["ai", "artificial intelligence", "generative", "genai", "llm", "gpt",
                  "chatbot", "rag"],
     "reason": "Builds on backend experience and creates a shorter transition path.",
     "skills": ["skill:python", "skill:http-apis", "skill:llm-apis", "skill:prompt-design",
                "skill:embeddings", "skill:rag-foundations", "skill:rag-evaluation",
                "skill:ai-deployment", "skill:ai-safety", "skill:portfolio"]},
    {"id": "target:ml-engineering", "title": "Machine Learning Engineering",
     "type": "career_transition", "target_role": "Machine Learning Engineer",
     "keywords": ["machine learning", "ml", "model training", "data science", "deep learning"],
     "reason": "Broader mathematical and model-training route.",
     "skills": ["skill:python", "skill:databases", "skill:embeddings", "skill:ai-eval",
                "skill:ai-deployment", "skill:portfolio"]},
    {"id": "target:ai-platform", "title": "AI Platform Engineering",
     "type": "career_transition", "target_role": "AI Engineer",
     "keywords": ["platform", "infrastructure", "mlops", "deployment", "serving"],
     "reason": "Stronger infrastructure and deployment focus.",
     "skills": ["skill:python", "skill:packaging", "skill:cloud-foundations", "skill:ai-deployment",
                "skill:llm-apis", "skill:ai-safety", "skill:portfolio"]},
    {"id": "target:ai-agents", "title": "Agentic AI Development",
     "type": "topic_mastery", "target_role": "AI Engineer",
     "keywords": ["agent", "agents", "agentic", "tool use", "autonomous", "mcp"],
     "reason": "Focused on tool-using, multi-step AI agents.",
     "skills": ["skill:python", "skill:llm-apis", "skill:prompt-design", "skill:agents",
                "skill:ai-eval", "skill:portfolio"]},
    {"id": "target:cloud-architecture", "title": "Cloud Solutions Architecture",
     "type": "topic_mastery", "target_role": "Cloud Solutions Architect",
     "keywords": ["cloud", "aws", "azure", "architecture", "solutions architect", "infrastructure"],
     "reason": "Secure, resilient cloud design fundamentals.",
     "skills": ["skill:cloud-foundations", "skill:iam", "skill:encryption",
                "skill:network-security", "skill:databases", "skill:portfolio"]},
]


# --- Accessors --------------------------------------------------------------

@lru_cache(maxsize=1)
def _skill_index() -> dict[str, SkillNode]:
    return {s["id"]: SkillNode(**s) for s in _SKILLS}


@lru_cache(maxsize=1)
def _occupation_index() -> dict[str, Occupation]:
    return {o["id"]: Occupation(**o) for o in _OCCUPATIONS}


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for s in _skill_index().values():
        idx[s.name.lower()] = s.id
        idx[s.id.lower()] = s.id
        for a in s.aliases:
            idx.setdefault(a.lower(), s.id)
    return idx


def all_skills() -> list[SkillNode]:
    return list(_skill_index().values())


def get_skill(skill_id: str) -> SkillNode | None:
    return _skill_index().get(skill_id)


def resolve_skill(name_or_id: str) -> SkillNode | None:
    """Resolve a skill by id, exact name, or alias (case-insensitive)."""
    if not name_or_id:
        return None
    key = name_or_id.strip().lower()
    sid = _alias_index().get(key)
    if sid:
        return _skill_index()[sid]
    # loose contains match as a last resort
    for name, sid in _alias_index().items():
        if key and (key in name or name in key):
            return _skill_index()[sid]
    return None


def search_skills(query: str, limit: int = 10) -> list[SkillNode]:
    q = (query or "").strip().lower()
    if not q:
        return all_skills()[:limit]
    scored: list[tuple[int, SkillNode]] = []
    for s in _skill_index().values():
        hay = " ".join([s.name, s.description, " ".join(s.aliases)]).lower()
        score = 0
        if q == s.name.lower():
            score += 5
        if q in hay:
            score += 2
        score += sum(1 for w in q.split() if w in hay)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:limit]]


def list_domains() -> list[dict]:
    """The Scout 2.0 domains, each with a count of occupations currently seeded."""
    counts: dict[str, int] = {}
    for o in _occupation_index().values():
        if o.domain:
            counts[o.domain] = counts.get(o.domain, 0) + 1
    return [{**d, "occupation_count": counts.get(d["id"], 0)} for d in DOMAINS]


def all_occupations() -> list[Occupation]:
    return list(_occupation_index().values())


def get_occupation(occupation_id: str) -> Occupation | None:
    return _occupation_index().get(occupation_id)


def resolve_occupation(name_or_id: str) -> Occupation | None:
    if not name_or_id:
        return None
    key = name_or_id.strip().lower()
    for o in _occupation_index().values():
        if key == o.id.lower() or key == o.name.lower() or key in [a.lower() for a in o.aliases]:
            return o
    for o in _occupation_index().values():
        hay = " ".join([o.name, " ".join(o.aliases)]).lower()
        if key and key in hay:
            return o
    return None


def search_occupations(query: str, limit: int = 10,
                       domain: str | None = None) -> list[Occupation]:
    q = (query or "").strip().lower()
    pool = [o for o in _occupation_index().values()
            if not domain or o.domain == domain]
    if not q:
        return pool[:limit]
    out = [o for o in pool
           if q in " ".join([o.name, o.description, " ".join(o.aliases)]).lower()]
    return out[:limit]


def learning_targets() -> list[dict]:
    return list(_TARGETS)


def get_target(target_id: str) -> dict | None:
    for t in _TARGETS:
        if t["id"] == target_id:
            return t
    return None


def target_to_candidate(target: dict) -> GoalCandidate:
    return GoalCandidate(
        id=target["id"],
        title=target["title"],
        type=target.get("type", "topic_mastery"),
        reason=target.get("reason", ""),
        target_role=target.get("target_role"),
        skills=list(target.get("skills", [])),
    )


def expand_prerequisites(skill_ids: list[str]) -> list[str]:
    """Return skill_ids plus all transitive prerequisites (deduplicated)."""
    seen: list[str] = []
    stack = list(skill_ids)
    while stack:
        sid = stack.pop()
        node = get_skill(sid)
        if node is None or sid in seen:
            continue
        seen.append(sid)
        stack.extend(node.prerequisites)
    return seen


def graph(skill_ids: list[str] | None = None) -> dict:
    """Return a ``{nodes, edges}`` view of the skill graph for visualization.

    When ``skill_ids`` is given, the graph is restricted to those skills plus
    their transitive prerequisites, ordered topologically so a UI can lay out
    layers left-to-right. Edges point prerequisite -> dependent.
    """
    if skill_ids is None:
        ids = [s.id for s in all_skills()]
    else:
        ids = expand_prerequisites(list(skill_ids))
    ordered = topological_sort(ids)
    depth = {sid: i for i, sid in enumerate(ordered)}
    idset = set(ids)
    nodes = []
    edges = []
    for sid in ordered:
        node = get_skill(sid)
        if not node:
            continue
        nodes.append({
            "id": sid,
            "name": node.name,
            "level": node.level,
            "durability": node.durability,
            "depth": depth[sid],
        })
        for pre in node.prerequisites:
            if pre in idset:
                edges.append({"from": pre, "to": sid})
    return {"nodes": nodes, "edges": edges}


def topological_sort(skill_ids: list[str]) -> list[str]:
    """Order skills so every prerequisite precedes its dependents (Kahn's algo).

    Only edges *within* the given set are considered. Cycles (which the seed
    graph does not contain) are broken deterministically by name to stay safe.
    """
    nodes = set(skill_ids)
    indegree = {sid: 0 for sid in nodes}
    adj: dict[str, list[str]] = {sid: [] for sid in nodes}
    for sid in nodes:
        node = get_skill(sid)
        if not node:
            continue
        for pre in node.prerequisites:
            if pre in nodes:
                adj[pre].append(sid)
                indegree[sid] += 1
    ready = sorted([sid for sid, d in indegree.items() if d == 0])
    order: list[str] = []
    while ready:
        sid = ready.pop(0)
        order.append(sid)
        for nxt in sorted(adj[sid]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort()
    # Append any remaining (would only happen on a cycle) deterministically.
    for sid in sorted(nodes):
        if sid not in order:
            order.append(sid)
    return order
