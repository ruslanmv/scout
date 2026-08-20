"""Tests for the Scout 2.0 Phase 3 universal signal layer."""
from __future__ import annotations

import json

import pytest

from app.collectors import adzuna_collector
from app.collectors.signal import Evidence, Signal


class _FakeResponse:
    def __init__(self, payload, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """Maps the ``what`` query param to a fabricated Adzuna count."""

    def __init__(self, counts: dict[str, int], *, fail: bool = False):
        self.counts = counts
        self.fail = fail
        self.calls: list[dict] = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params})
        if self.fail:
            return _FakeResponse({}, status=500)
        role = (params or {}).get("what", "")
        return _FakeResponse({"count": self.counts.get(role, 0)})


# --- Signal model -----------------------------------------------------------

def test_signal_key_is_stable_and_region_normalized():
    a = Signal(subject="Data Analyst", domain="tech-data", region="Germany", source="adzuna")
    b = Signal(subject="data analyst", domain="tech-data", region="germany", source="adzuna")
    assert a.key() == b.key()
    worldwide = Signal(subject="Nurse", domain="health", source="adzuna")
    assert worldwide.key() == "adzuna:health:worldwide:nurse"


def test_signal_measures_default_to_zero():
    s = Signal(subject="Chef", domain="hospitality-service", source="adzuna")
    assert s.demand == 0.0 and s.momentum == 0.0 and s.sample_size == 0
    assert s.evidence == []


# --- demand normalization ---------------------------------------------------

def test_demand_is_bounded_and_monotonic():
    assert adzuna_collector._demand_from_count(0) == 0.0
    low = adzuna_collector._demand_from_count(10)
    high = adzuna_collector._demand_from_count(10000)
    capped = adzuna_collector._demand_from_count(10_000_000)
    assert 0.0 < low < high <= 1.0
    assert capped <= 1.0


def test_country_code_mapping_and_fallback():
    assert adzuna_collector._country_code("Germany") == "de"
    assert adzuna_collector._country_code("United States") == "us"
    assert adzuna_collector._country_code(None) == "gb"
    assert adzuna_collector._country_code("Narnia") == "gb"  # unknown -> widest catalog


# --- keyless / fail-safe behavior ------------------------------------------

def test_collect_returns_empty_without_credentials(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    assert adzuna_collector.collect_role_signals(["Data Analyst"], country="Germany") == []


def test_collect_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "key")
    session = _FakeSession({}, fail=True)
    out = adzuna_collector.collect_role_signals(
        ["Data Analyst"], country="Germany", session=session
    )
    assert out == []


# --- happy path -------------------------------------------------------------

def test_collect_normalizes_counts_and_skips_zero(monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "key")
    session = _FakeSession({"Data Analyst": 5000, "Data Scientist": 0})
    out = adzuna_collector.collect_role_signals(
        ["Data Analyst", "Data Scientist"],
        domain="tech-data",
        country="Germany",
        city="Berlin",
        session=session,
    )
    # Zero-count role is skipped (no fabricated demand).
    assert [s.subject for s in out] == ["Data Analyst"]
    sig = out[0]
    assert sig.source == "adzuna"
    assert sig.domain == "tech-data"
    assert sig.region == "Berlin"
    assert 0.0 < sig.demand <= 1.0
    assert sig.sample_size == 5000
    assert sig.evidence and sig.evidence[0].url.startswith("https://www.adzuna.com/")
    assert sig.extra["adzuna_country"] == "de"


# --- collect_signals script -------------------------------------------------

def test_collect_signals_script_writes_valid_doc(tmp_path, monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    from scripts import collect_signals

    signals = collect_signals.collect(["Worldwide"], max_roles=2)
    doc = collect_signals.build_document(signals, ["Worldwide"])
    # Keyless => empty but valid.
    assert doc["count"] == 0
    assert doc["sources"] == []
    assert "signals" in doc and isinstance(doc["signals"], list)
    # Document round-trips through JSON.
    assert json.loads(json.dumps(doc))["note"]
