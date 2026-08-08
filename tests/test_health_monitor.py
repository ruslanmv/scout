"""Tests for the source & API health monitor.

An injected fake probe keeps these fully offline and deterministic — no real
network calls — while still exercising classification, aggregation, snapshot
persistence, and the API surface.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import health_monitor as hm

client = TestClient(app)


def _fake_probe(mapping: dict[str, tuple]):
    """Build a probe that returns a canned (status, latency, error) per URL,
    matched by substring; unmatched URLs default to a healthy 200."""
    def probe(url: str):
        for needle, result in mapping.items():
            if needle in url:
                return result
        return (200, 15, None)
    return probe


def test_classify_rules():
    course = {"category": "course_url"}
    api = {"category": "signal_source"}
    assert hm.classify(api, 200, None)[0] == "up"
    assert hm.classify(api, 403, None)[0] == "up"          # reachable, auth
    assert hm.classify(api, 429, None)[0] == "degraded"    # rate limited
    assert hm.classify(api, 500, None)[0] == "down"
    assert hm.classify(api, None, "ConnectTimeout")[0] == "down"
    # 404 is strict for a course (gone) but soft for an API base (moved)
    assert hm.classify(course, 404, None)[0] == "down"
    assert hm.classify(api, 404, None)[0] == "degraded"


def test_run_health_check_aggregates_and_counts():
    probe = _fake_probe({
        "postgresql": (404, 10, None),          # a dead course URL -> down
        "api.github.com": (429, 20, None),      # rate limited -> degraded
    })
    snap = hm.run_health_check(probe=probe)
    assert snap["overall"] == "down"            # a course is down
    assert snap["counts"].get("down", 0) >= 1
    assert snap["counts"].get("degraded", 0) >= 1
    # every check carries the required fields
    for c in snap["checks"]:
        assert {"name", "category", "url", "status", "checked_at"} <= set(c)
    assert "by_category" in snap and "course_url" in snap["by_category"]


def test_missing_api_key_is_skipped_not_down(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    snap = hm.run_health_check(probe=_fake_probe({}))
    skipped = [c for c in snap["checks"] if c["status"] == "skipped"]
    names = {c["name"] for c in skipped}
    assert {"Tavily Search", "Brave Search", "YouTube Data API"} <= names


def test_config_only_probe_is_offline():
    snap = hm.run_health_check(probe=False)
    # nothing is "up"/"down" — network targets are unknown, keyless are skipped
    statuses = {c["status"] for c in snap["checks"]}
    assert statuses <= {"unknown", "skipped"}


def test_snapshot_save_and_load(tmp_path: Path):
    snap = hm.run_health_check(probe=_fake_probe({}))
    paths = hm.save_snapshot(snap, tmp_path / "health")
    assert Path(paths["latest"]).exists() and Path(paths["dated"]).exists()
    loaded = hm.load_latest_snapshot(tmp_path / "health")
    assert loaded["overall"] == snap["overall"]
    assert hm.load_latest_snapshot(tmp_path / "does-not-exist") is None


def test_api_health_sources_and_summary():
    r = client.get("/api/v1/health/sources")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] in ("cached_snapshot", "config_only")
    assert "checks" in body and "overall" in body

    s = client.get("/api/v1/health/sources/summary").json()
    assert "overall" in s and "counts" in s and "needs_attention" in s


def test_liveness_endpoint():
    assert client.get("/api/v1/health").json()["status"] == "ok"
