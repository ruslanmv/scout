"""Tests for the Scout MCP tool logic (no MCP SDK required)."""
from scout_mcp import tools


def test_parse_location():
    assert tools.parse_location("Rome, Italy") == ("Italy", "Rome")
    assert tools.parse_location("Worldwide") == ("Worldwide", None)
    assert tools.parse_location("San Francisco, United States") == ("United States", "San Francisco")


def test_list_hot_trends():
    out = tools.list_hot_trends("Worldwide", 3)
    assert out["count"] == 3
    assert out["trends"] and all("name" in t and "build_idea" in t for t in out["trends"])


def test_recommend_what_to_build():
    out = tools.recommend_what_to_build("startup", "founder", "Italy, Rome", 2)
    recs = out["recommendations"]
    assert len(recs) == 2
    assert all("next_move" in r and r["next_move"]["build"] for r in recs)


def test_brainstorm_and_resolve_by_name():
    out = tools.brainstorm_project_ideas("AI Agents", 2)  # fuzzy name -> id
    assert out["topic_id"] == "ai-agents"
    assert 1 <= len(out["project_blueprints"]) <= 2


def test_brainstorm_unknown_topic():
    out = tools.brainstorm_project_ideas("totally-made-up-topic")
    assert "error" in out and "hint" in out


def test_search_trends_ranks_matches():
    out = tools.search_trends("agents", 5)
    assert out["results"] and "agents" in out["results"][0]["name"].lower()


def test_find_build_opportunities():
    out = tools.find_build_opportunities("Worldwide", "create_agents", 4)
    assert out["opportunities"] and all("recommended_agent" in o for o in out["opportunities"])
