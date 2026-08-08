"""Tests for the Scout Learning Navigator deterministic pipeline.

These verify the core product invariants (spec sections 10, 11, 17, 22): the
path is built by deterministic logic, prerequisites always precede dependents,
resources carry provenance, and unverifiable claims are labelled rather than
asserted.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.providers import base as providers
from app.services.learning import (
    course_ranker,
    orchestrator,
    skill_gap,
    taxonomy,
)
from app.services.learning.schemas import (
    Budget,
    LearningGoalRequest,
    ProgressEvent,
    ResourceQuery,
    SkillRef,
)

client = TestClient(app)


def _career_request(**overrides) -> LearningGoalRequest:
    base = dict(
        intent="advance_career",
        query="become an AI engineer",
        target_role="AI Engineer",
        current_role="backend developer",
        current_skills=[SkillRef(name="Python", level="intermediate")],
        country="Italy",
        city="Rome",
        hours_per_week=8,
    )
    base.update(overrides)
    return LearningGoalRequest(**base)


# --- Taxonomy / graph -------------------------------------------------------

def test_topological_sort_respects_prerequisites():
    ids = taxonomy.expand_prerequisites(["skill:rag-evaluation"])
    order = taxonomy.topological_sort(ids)
    assert order.index("skill:python") < order.index("skill:embeddings")
    assert order.index("skill:rag-foundations") < order.index("skill:rag-evaluation")
    assert order.index("skill:embeddings") < order.index("skill:rag-foundations")


def test_resolve_skill_by_alias():
    assert taxonomy.resolve_skill("retrieval augmented generation").id == "skill:rag-foundations"
    assert taxonomy.resolve_skill("Python").id == "skill:python"


def test_expand_prerequisites_is_transitive():
    got = set(taxonomy.expand_prerequisites(["skill:rag-foundations"]))
    assert {"skill:python", "skill:embeddings", "skill:llm-apis"} <= got


# --- Goal resolution --------------------------------------------------------

def test_resolve_topic_goal_picks_relevant_target():
    req = LearningGoalRequest(intent="learn_topic", query="I want to learn artificial intelligence")
    resolved = orchestrator.resolve_goal(req)
    assert resolved.recommended.title
    assert len(resolved.alternatives) >= 1
    # alternatives must be distinct from the recommendation
    assert all(a.id != resolved.recommended.id for a in resolved.alternatives)


def test_location_effect_is_explained_and_optional():
    with_loc = orchestrator.resolve_goal(_career_request())
    assert with_loc.location_effect and "Italy" in with_loc.location_effect
    # It must never claim location changes prerequisites.
    assert "prerequisite" in with_loc.location_effect.lower()
    without = orchestrator.resolve_goal(_career_request(use_location=False))
    assert without.location_effect is None


def test_certification_goal_resolves_to_official_cert():
    req = LearningGoalRequest(intent="prepare_certification",
                              query="AWS Solutions Architect Associate",
                              target_certification="AWS Solutions Architect Associate")
    resolved = orchestrator.resolve_goal(req)
    assert resolved.recommended.type == "certification"
    assert resolved.recommended.target_certification == "cert:aws-saa"


# --- Skill gap --------------------------------------------------------------

def test_skill_gap_marks_known_and_missing():
    req = _career_request()
    goal = orchestrator.resolve_goal(req).recommended
    gap = skill_gap.calculate(goal, req)
    assert "skill:python" in gap.known_skill_ids
    assert "skill:python" not in gap.missing_skill_ids
    assert "skill:llm-apis" in gap.missing_skill_ids
    # ordering is topological over the whole required set
    order = gap.ordered_skill_ids
    assert order.index("skill:embeddings") < order.index("skill:rag-foundations")


# --- Ranking ----------------------------------------------------------------

def test_ranker_returns_score_reasons_and_warnings():
    req = _career_request()
    goal = orchestrator.resolve_goal(req).recommended
    gap = skill_gap.calculate(goal, req)
    resources = providers.search_all(ResourceQuery(skills=gap.missing_skill_ids, limit=40))
    ranked = course_ranker.rank(resources, gap, req, mode="career")
    assert ranked
    top = ranked[0]
    assert 0 <= top.score <= 100
    assert top.reasons
    # ranking is sorted descending
    assert all(ranked[i].score >= ranked[i + 1].score for i in range(len(ranked) - 1))


def test_free_only_filter_blocks_unverifiable_access():
    req = _career_request(budget=Budget(free_only=True))
    goal = orchestrator.resolve_goal(req).recommended
    gap = skill_gap.calculate(goal, req)
    # A search-discovered resource with unknown access must be filtered out.
    from app.services.learning.schemas import (
        LearningResource,
        ResourceAccess,
        ResourceProvenance,
    )
    discovered = LearningResource(
        id="resource:udemy:test", provider="udemy", title="Some Udemy course",
        url="https://udemy.com/course/x", skills_taught=["skill:llm-apis"],
        access=ResourceAccess(type="unknown", observed_at=None),
        provenance=ResourceProvenance(source_type="web_search", source_url="x"))
    ranked = course_ranker.rank([discovered], gap, req, mode="career")
    assert ranked == []


def test_web_discovered_resource_shows_verify_on_provider():
    from app.services.learning.schemas import (
        LearningResource,
        ResourceAccess,
        ResourceProvenance,
    )
    r = LearningResource(
        id="resource:udemy:y", provider="udemy", title="X", url="https://udemy.com/course/y",
        access=ResourceAccess(type="unknown", observed_at=None),
        provenance=ResourceProvenance(source_type="web_search", source_url="y"))
    assert r.price_display() == "Verify on provider"


# --- Path generation (end to end) -------------------------------------------

def test_generate_path_orders_prerequisites_first():
    req = _career_request()
    resolved = orchestrator.resolve_goal(req)
    path = orchestrator.generate_path(req, resolved_goal_id=resolved.id)
    assert path.stages
    assert path.source == "deterministic"

    # Build a stage index per taught skill and assert every graph prerequisite
    # appears in an equal-or-earlier stage.
    stage_of = {}
    for stage in path.stages:
        for sr in stage.resources:
            for sid in sr.primary.resource.skills_taught:
                stage_of.setdefault(sid, stage.stage)
    for sid, st in stage_of.items():
        node = taxonomy.get_skill(sid)
        for pre in (node.prerequisites if node else []):
            if pre in stage_of:
                assert stage_of[pre] <= st, f"{pre} scheduled after {sid}"


def test_generated_path_has_no_hard_validation_errors():
    req = _career_request()
    resolved = orchestrator.resolve_goal(req)
    path = orchestrator.generate_path(req, resolved_goal_id=resolved.id)
    from app.services.learning import validator
    ok, _ = validator.validate(path)
    assert ok


def test_stages_carry_provenance_and_projects():
    req = _career_request()
    path = orchestrator.generate_path(req)
    for stage in path.stages:
        for sr in stage.resources:
            assert sr.primary.resource.url
            assert sr.primary.resource.provenance.source_type
        assert stage.assessment is not None


def test_certification_path_covers_all_exam_domain_skills():
    req = LearningGoalRequest(intent="prepare_certification",
                              query="AWS Solutions Architect Associate",
                              target_certification="cert:aws-saa", hours_per_week=6)
    resolved = orchestrator.resolve_goal(req)
    path = orchestrator.generate_path(req, resolved_goal_id=resolved.id)
    assert path.uncovered_skills == []
    taught = {sid for s in path.stages for sr in s.resources
              for sid in sr.primary.resource.skills_taught}
    from app.services.learning import certifications
    cert = certifications.get_certification("cert:aws-saa")
    assert set(cert.skills()) <= taught


def test_certification_prep_track_is_a_typed_sequence():
    req = LearningGoalRequest(intent="prepare_certification",
                              query="Claude Certified Architect",
                              target_certification="Claude Certified Architect", hours_per_week=8)
    resolved = orchestrator.resolve_goal(req)
    assert resolved.recommended.target_certification == "cert:claude-architect"
    path = orchestrator.generate_path(req, resolved_goal_id=resolved.id)
    titles = [s.title for s in path.stages]
    # The canonical prep order (spec section 7 / the study-path example).
    assert titles[0].startswith("Start with the official training")
    assert any("Build along" in t for t in titles)
    assert any("pillars" in t for t in titles)
    assert any("exam guide" in t for t in titles)
    assert any("practice" in t for t in titles)
    assert any("Build 3 real projects" in t for t in titles)
    assert titles[-1].startswith("Register")
    # foundations phase covers the prerequisites, nothing left uncovered
    assert path.uncovered_skills == []
    from app.services.learning import validator
    assert validator.validate(path)[0]


def test_paid_exam_items_show_verify_on_provider():
    from app.providers.static_catalog import StaticCatalogProvider
    from app.services.learning.schemas import ResourceQuery
    catalog = {r.id: r for r in StaticCatalogProvider().search(ResourceQuery(limit=300))}
    register = catalog["resource:static:claude-register"]
    assert register.access.type == "unknown"
    assert register.price_display() == "Verify on provider"
    # Free official docs still read as free (they carry a recent observation).
    academy = catalog["resource:static:anthropic-academy"]
    assert academy.price_display() == "Free"


def test_every_stage_gets_a_stable_unique_id():
    req = _career_request()
    path = orchestrator.generate_path(req)
    ids = [s.stage_id for s in path.stages]
    assert all(ids) and len(set(ids)) == len(ids)   # populated and unique
    assert all(s.stage_id.startswith(f"s{s.stage}-") for s in path.stages)


def test_career_path_ends_with_portfolio_capstone():
    req = _career_request()
    path = orchestrator.generate_path(req)
    last = path.stages[-1]
    assert "portfolio" in last.title.lower()
    assert last.project is not None


def test_fallback_path_when_no_resources():
    # A query whose skills exist but with providers yielding nothing usable:
    # force the fallback by requesting free_only against a graph with no free
    # match for an obscure skill set is hard, so call the fallback directly.
    from app.services.learning import fallback
    req = _career_request()
    goal = orchestrator.resolve_goal(req).recommended
    gap = skill_gap.calculate(goal, req)
    path = fallback.build_fallback_path("path_test", goal, gap, req)
    assert path.source == "deterministic-fallback"
    assert path.stages
    assert path.warnings


# --- Progress & replan ------------------------------------------------------

def test_replan_folds_completed_stages_into_known_skills():
    req = _career_request()
    path = orchestrator.generate_path(req)
    original_stages = len(path.stages)
    orchestrator.record_progress(ProgressEvent(path_id=path.path_id, stage=1, status="completed"))
    orchestrator.record_progress(ProgressEvent(path_id=path.path_id, stage=2, status="completed"))
    new_path = orchestrator.replan(path.path_id, req)
    assert new_path is not None
    assert new_path.replan_after["completed_stages"] == 2
    assert len(new_path.stages) <= original_stages


# --- API ---------------------------------------------------------------------

def test_api_resolve_goal():
    r = client.post("/api/v1/learning/goals/resolve",
                    json={"intent": "learn_topic", "query": "I want to learn AI"})
    assert r.status_code == 200
    body = r.json()
    assert body["recommended"]["title"]
    assert "alternatives" in body


def test_api_create_get_progress_path():
    r = client.post("/api/v1/learning/paths", json={
        "request": {"intent": "advance_career", "query": "become an AI engineer",
                    "target_role": "AI Engineer",
                    "current_skills": [{"name": "Python", "level": "intermediate"}],
                    "hours_per_week": 8},
    })
    assert r.status_code == 200
    path_id = r.json()["path_id"]
    assert client.get(f"/api/v1/learning/paths/{path_id}").status_code == 200
    pr = client.patch(f"/api/v1/learning/paths/{path_id}/progress",
                      json={"stage": 1, "status": "completed"})
    assert pr.status_code == 200
    assert pr.json()["progress"]


def test_api_path_requires_a_target():
    r = client.post("/api/v1/learning/paths", json={"request": {}})
    assert r.status_code == 422


def test_api_get_missing_path_is_404():
    assert client.get("/api/v1/learning/paths/path_does_not_exist").status_code == 404


def test_api_skill_gap_endpoint():
    r = client.post("/api/v1/learning/skill-gap", json={
        "request": {"intent": "advance_career", "query": "become an AI engineer",
                    "target_role": "AI Engineer",
                    "current_skills": [{"name": "Python", "level": "intermediate"}],
                    "country": "Italy"}})
    assert r.status_code == 200
    body = r.json()
    assert "Python" in [k["name"] for k in body["known"]]
    assert body["missing"] and all("priority" in m for m in body["missing"])
    assert body["ordered_skill_ids"]


def test_api_skills_graph_focus_and_full():
    focused = client.get("/api/v1/skills/graph?skills=skill:rag-evaluation").json()
    node_ids = [n["id"] for n in focused["nodes"]]
    assert "skill:rag-evaluation" in node_ids
    assert "skill:python" in node_ids  # transitive prerequisite pulled in
    # edges point prerequisite -> dependent and depth is ordered
    assert all(e["from"] in node_ids and e["to"] in node_ids for e in focused["edges"])
    full = client.get("/api/v1/skills/graph").json()
    assert len(full["nodes"]) >= len(focused["nodes"])


def test_skill_graph_depth_orders_prerequisites_before_dependents():
    g = taxonomy.graph(["skill:rag-foundations"])
    depth = {n["id"]: n["depth"] for n in g["nodes"]}
    assert depth["skill:python"] < depth["skill:embeddings"] < depth["skill:rag-foundations"]


def test_api_knowledge_and_provider_endpoints():
    assert client.get("/api/v1/skills/search?q=rag").json()["results"]
    assert client.get("/api/v1/occupations/search?q=ai").json()["results"]
    assert client.get("/api/v1/certifications/search?q=aws").json()["results"]
    health = client.get("/api/v1/providers/health").json()["providers"]
    names = {p["provider"] for p in health}
    assert "static_catalog" in names


# --- MCP tools --------------------------------------------------------------

def test_mcp_generate_learning_path():
    from scout_mcp import tools
    out = tools.generate_learning_path(
        "become an AI engineer", "Python backend developer", ["Python"],
        "Rome, Italy", 8, 100, "advance_career")
    assert out["stages"]
    assert out["goal"]
    assert out["estimated_weeks"] > 0


def test_mcp_evaluate_skill_gap_counts_known_skill():
    from scout_mcp import tools
    out = tools.evaluate_skill_gap("AI Engineer", ["Python"], "Rome, Italy")
    assert "Python" in out["already_known"]
    assert all(m["name"] != "Python" for m in out["missing"])
