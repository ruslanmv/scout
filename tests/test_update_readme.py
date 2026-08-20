"""Tests for the dynamic README trends section generator."""
from __future__ import annotations

from scripts import update_readme as ur

_DATA = {
    "generated_at": "2026-08-18T00:00:00+00:00",
    "topics": [
        {
            "id": "ai-agents",
            "name": "AI Agents",
            "skills": ["Python", "LangGraph"],
            "signals": {"job_demand": 90, "career_value": 95, "github_growth": 90,
                        "ecosystem_fit": 99, "project_potential": 96},
        },
        {
            "id": "rag",
            "name": "RAG",
            "skills": ["Python", "Embeddings"],
            "signals": {"job_demand": 70, "career_value": 70, "github_growth": 60,
                        "ecosystem_fit": 70, "project_potential": 70},
        },
    ],
    "local_boosts": {
        "united-states:san francisco": {"ai-agents": 6, "rag": 3},
        "italy:rome": {"rag": 4},
    },
}


def test_topic_demand_blend_is_bounded():
    d = ur._topic_demand(_DATA["topics"][0])
    assert 0 <= d <= 100
    # Higher signals -> higher demand than the weaker topic.
    assert d > ur._topic_demand(_DATA["topics"][1])


def test_meter_width_and_fill():
    assert ur._meter(0) == "░" * ur._METER_WIDTH
    assert ur._meter(100) == "█" * ur._METER_WIDTH
    mid = ur._meter(50)
    assert len(mid) == ur._METER_WIDTH and "█" in mid and "░" in mid


def test_top_skills_ranks_by_summed_demand():
    skills = ur._top_skills(_DATA["topics"], limit=5)
    names = [s["skill"] for s in skills]
    # Python appears in both topics -> highest summed weight -> ranked first.
    assert names[0] == "Python"
    assert set(names) == {"Python", "LangGraph", "Embeddings"}
    py = skills[0]
    assert py["count"] == 2 and py["driver"] == "AI Agents"


def test_topics_by_place_includes_worldwide_and_boosts():
    rows = dict(ur._topics_by_place(_DATA))
    assert "🌍 Worldwide" in rows
    # Worldwide ordered by demand: AI Agents before RAG.
    assert rows["🌍 Worldwide"][0] == "AI Agents"
    # SF boosts rank ai-agents first.
    assert rows["🇺🇸 San Francisco"][0] == "AI Agents"


def test_render_section_has_markers_and_tables():
    out = ur.render_section(_DATA, None)
    assert out.startswith(ur.START) and out.rstrip().endswith(ur.END)
    assert "Top skills to learn" in out
    assert "What's hot by place" in out
    # No signals doc -> no live-demand table.
    assert "Live job demand" not in out


def test_render_section_includes_live_demand_when_signals_present():
    signals_doc = {
        "generated_at": "2026-08-18T00:00:00+00:00",
        "signals": [
            {"subject": "Data Analyst", "subject_kind": "role", "domain": "tech-data",
             "region": "Germany", "sample_size": 5000},
            {"subject": "Nurse", "subject_kind": "role", "domain": "health",
             "region": "Worldwide", "sample_size": 12000},
        ],
    }
    out = ur.render_section(_DATA, signals_doc)
    assert "Live job demand" in out
    # Ranked by postings: Nurse (12k) before Data Analyst (5k).
    assert out.index("Nurse") < out.index("Data Analyst")
    assert "12,000" in out


def test_replace_block_is_idempotent():
    readme = f"pre\n{ur.START}\nold\n{ur.END}\npost\n"
    section = f"{ur.START}\nnew\n{ur.END}"
    once = ur._replace_block(readme, section)
    assert once is not None and "new" in once and "old" not in once
    # Applying again with the same section yields the same result.
    assert ur._replace_block(once, section) == once


def test_replace_block_missing_markers_returns_none():
    assert ur._replace_block("no markers here", "x") is None
