"""Tests for the nightly AI-batch (Scout 2.0 §5–6) and the serving order.

Fully offline: the single LLM entrypoint (``ai_advisor.live_plan``) is
monkeypatched, and batch plans are written to a temp dir, so no network is used.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services import ai_advisor
from app.services.recommender import load_topics


def _topic() -> dict:
    return load_topics()[0]


def test_batch_key_is_stable_and_slugged():
    k = ai_advisor.batch_key("ai-agents", "United States", "San Francisco", "career", "developer")
    assert k == "ai-agents__united-states__san-francisco__career__developer"
    # missing location components get safe placeholders
    assert ai_advisor.batch_key("rag", "Worldwide", None, "build_portfolio", "student") \
        == "rag__worldwide__any__build-portfolio__student"


def test_content_hash_changes_with_signals():
    t = _topic()
    h1 = ai_advisor.batch_content_hash(t, "Italy", "Rome", "career", "developer")
    t2 = dict(t)
    t2["signals"] = {**t.get("signals", {}), "job_demand": (t.get("signals", {}).get("job_demand", 0) + 5)}
    h2 = ai_advisor.batch_content_hash(t2, "Italy", "Rome", "career", "developer")
    assert h1 != h2                              # ranking changed → re-narrate
    # same inputs → same hash (deterministic)
    assert h1 == ai_advisor.batch_content_hash(t, "Italy", "Rome", "career", "developer")


def test_load_batch_plan_tags_source(tmp_path: Path):
    t = _topic()
    key = ai_advisor.batch_key(t["id"], "Worldwide", None, "career", "developer")
    (tmp_path / f"{key}.json").write_text(json.dumps(
        {"topic_id": t["id"], "headline": "cached", "source": "ollabridge-cloud"}), encoding="utf-8")
    plan = ai_advisor.load_batch_plan(t, "Worldwide", None, "career", "developer", base_dir=tmp_path)
    assert plan is not None and plan["source"] == "ai-batch"
    assert ai_advisor.load_batch_plan(t, "Worldwide", None, "career", "developer",
                                      base_dir=tmp_path / "missing") is None


def test_serving_order_live_then_batch_then_template(monkeypatch, tmp_path: Path):
    t = _topic()
    monkeypatch.setattr(ai_advisor, "AI_PLANS_DIR", tmp_path)

    # 1) live AI available → live wins
    monkeypatch.setattr(ai_advisor, "live_plan",
                        lambda *a, **k: {"topic_id": t["id"], "source": "ollabridge-cloud", "headline": "live"})
    assert ai_advisor.generate_plan(t, "Worldwide", None, "career", "developer")["source"] == "ollabridge-cloud"

    # 2) live unavailable, a batch plan exists → serve the batch plan
    monkeypatch.setattr(ai_advisor, "live_plan", lambda *a, **k: None)
    key = ai_advisor.batch_key(t["id"], "Worldwide", None, "career", "developer")
    (tmp_path / f"{key}.json").write_text(json.dumps(
        {"topic_id": t["id"], "headline": "from yesterday"}), encoding="utf-8")
    served = ai_advisor.generate_plan(t, "Worldwide", None, "career", "developer")
    assert served["source"] == "ai-batch" and served["headline"] == "from yesterday"

    # 3) live unavailable and no batch plan → deterministic template (last resort)
    (tmp_path / f"{key}.json").unlink()
    template = ai_advisor.generate_plan(t, "Worldwide", None, "career", "developer")
    assert template["source"] == "deterministic"


def test_narrate_batch_writes_and_skips_unchanged(monkeypatch, tmp_path: Path):
    import scripts.narrate_batch as nb

    # AI "enabled" + a deterministic fake narrator (no network)
    orig_settings = ai_advisor.runtime_settings.get_settings
    monkeypatch.setattr(ai_advisor.runtime_settings, "get_settings",
                        lambda: {**orig_settings(), "ai_enabled": True})
    calls = {"n": 0}

    def fake_live(topic, country, city, goal, profile, settings=None):
        calls["n"] += 1
        return ai_advisor._assemble_ai_plan({"headline": "x"}, topic, country, city, goal, profile,
                                            source="ollabridge-cloud", provider="t", model="t")

    monkeypatch.setattr(ai_advisor, "live_plan", fake_live)
    out = tmp_path / "ai_plans"
    monkeypatch.setattr("sys.argv", ["narrate_batch", "--out", str(out), "--max-cells", "6", "--top-topics", "1"])
    nb.main()
    n_files = len([f for f in out.glob("*.json") if f.name != "index.json"])
    assert n_files >= 1 and (out / "index.json").exists()
    first_calls = calls["n"]

    # second run, nothing changed → cells are skipped (no new narration calls)
    monkeypatch.setattr("sys.argv", ["narrate_batch", "--out", str(out), "--max-cells", "6", "--top-topics", "1"])
    nb.main()
    index = json.loads((out / "index.json").read_text())
    assert index["ai_enabled"] is True and index["count"] >= 1
    assert calls["n"] == first_calls              # unchanged cells were not re-narrated
