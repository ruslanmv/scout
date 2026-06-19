"""Tests for the live AI plan endpoint and the admin-only settings API."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import runtime_settings

client = TestClient(app)


@pytest.fixture
def runtime_env(tmp_path, monkeypatch):
    """Isolate runtime overrides to a temp file and disable real AI calls."""
    monkeypatch.setenv("SCOUT_RUNTIME_CONFIG", str(tmp_path / "settings.json"))
    monkeypatch.setenv("SCOUT_AI_ENABLED", "0")  # force deterministic fallback (no network)
    runtime_settings.reset_overrides()
    yield monkeypatch
    runtime_settings.reset_overrides()


def test_ai_status_shape(runtime_env):
    data = client.get("/api/v1/ai/status").json()
    assert data["ai_enabled"] is False
    assert "provider" in data and "model" in data


def test_ai_plan_falls_back_without_network(runtime_env):
    """AI disabled -> deterministic plan with the same contract as the AI path."""
    resp = client.post("/api/v1/ai/plan", json={
        "topic_id": "ai-agents", "country": "Italy", "city": "Rome",
        "goal": "build_portfolio", "profile": "developer",
    })
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["source"] == "deterministic"
    assert isinstance(plan["study"], list) and plan["study"]
    assert isinstance(plan["build"], dict) and plan["build"]["title"]
    assert isinstance(plan["publish"], list)


def test_ai_plan_unknown_topic_404(runtime_env):
    resp = client.post("/api/v1/ai/plan", json={"topic_id": "does-not-exist"})
    assert resp.status_code == 404


def test_admin_locked_without_key(runtime_env):
    runtime_env.delenv("SCOUT_ADMIN_KEY", raising=False)
    assert client.get("/api/v1/admin/enabled").json() == {"enabled": False}
    assert client.get("/api/v1/admin/settings").status_code == 503


def test_admin_requires_valid_key(runtime_env):
    runtime_env.setenv("SCOUT_ADMIN_KEY", "s3cret")
    assert client.get("/api/v1/admin/enabled").json() == {"enabled": True}
    assert client.get("/api/v1/admin/settings").status_code == 401
    assert client.get("/api/v1/admin/settings", headers={"X-Admin-Key": "wrong"}).status_code == 401

    ok = client.get("/api/v1/admin/settings", headers={"X-Admin-Key": "s3cret"})
    assert ok.status_code == 200
    body = ok.json()
    # Secret must never be returned to the browser.
    assert "ai_api_key" not in body["settings"]
    assert "ai_api_key_set" in body["settings"]


def test_admin_can_update_settings(runtime_env):
    runtime_env.setenv("SCOUT_ADMIN_KEY", "s3cret")
    headers = {"X-Admin-Key": "s3cret"}
    saved = client.post("/api/v1/admin/settings", headers=headers,
                        json={"ai_model": "free-best", "ai_enabled": True})
    assert saved.status_code == 200
    assert saved.json()["settings"]["ai_model"] == "free-best"
    # Persisted across a fresh read.
    again = client.get("/api/v1/admin/settings", headers=headers).json()
    assert again["settings"]["ai_model"] == "free-best"


def test_normalize_base_url_resolves_hf_space_page():
    from app.services.runtime_settings import DEFAULT_BASE_URL, normalize_base_url
    endpoint = "https://ruslanmv-ollabridge.hf.space/v1"
    # Space page URL -> direct API endpoint.
    assert normalize_base_url("https://huggingface.co/spaces/ruslanmv/ollabridge") == endpoint
    # Already-direct forms are preserved / completed with /v1.
    assert normalize_base_url("https://ruslanmv-ollabridge.hf.space") == endpoint
    assert normalize_base_url("https://ruslanmv-ollabridge.hf.space/v1") == endpoint
    # Empty falls back to the default.
    assert normalize_base_url("") == DEFAULT_BASE_URL


def test_admin_save_normalizes_space_page_url(runtime_env):
    runtime_env.setenv("SCOUT_ADMIN_KEY", "s3cret")
    headers = {"X-Admin-Key": "s3cret"}
    saved = client.post("/api/v1/admin/settings", headers=headers,
                        json={"ai_base_url": "https://huggingface.co/spaces/ruslanmv/ollabridge"})
    assert saved.json()["settings"]["ai_base_url"] == "https://ruslanmv-ollabridge.hf.space/v1"
