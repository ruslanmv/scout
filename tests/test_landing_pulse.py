"""Landing Pulse: evidence classification, history and static contracts."""
import csv
import json
from pathlib import Path

from scripts.build_pulse import build_pulse, write_pulse


def _topics():
    return {"topics": [
        {"name": "AI", "skills": ["Python", "FastAPI", "Docker"],
         "signals": {"job_demand": 85, "career_value": 90, "github_growth": 80}},
        {"name": "Data", "skills": ["Python", "SQL", "Docker"],
         "signals": {"job_demand": 70, "career_value": 80}},
    ]}


def test_pulse_is_explicit_about_unavailable_hiring_data():
    feed = build_pulse(_topics(), {"signals": []}, "2026-10-14T08:00:00+00:00")
    assert feed["regions"]["Worldwide"]["status"] == "curated"
    assert len(feed["regions"]["Worldwide"]["items"]) == 8
    assert feed["source_status"] == "unavailable"
    assert feed["display"] == {"professions": 5, "skills": 5, "tools": 5}
    assert "Python" in [item["name"] for item in feed["skills"][:3]]
    assert feed["skills"][0]["source"] == "topic_proxy"
    assert all(x["source"] == "topic_proxy" for x in feed["tools"])
    localized = build_pulse({**_topics(), "local_boosts": {"italy:rome": {"AI": 20}}}, {"signals": []},
                            "2026-10-14T08:00:00+00:00")
    assert "italy:rome" in localized["skills_by_region"]
    assert localized["skills_by_region"]["italy:rome"][0]["score"] >= feed["skills"][0]["score"]


def test_measured_region_does_not_claim_a_sparse_or_global_ranking():
    signals = [
        {"subject_kind": "role", "subject": f"Role {i}", "region": "Italy",
         "sample_size": i * 10, "demand": 0.5, "source": "adzuna"}
        for i in range(1, 7)
    ]
    signals.append({"subject_kind": "role", "subject": "Nurse", "region": "Worldwide",
                    "sample_size": 9999, "source": "adzuna"})
    feed = build_pulse(_topics(), {"signals": signals}, "2026-10-14T08:00:00+00:00")
    assert feed["regions"]["Italy"]["status"] == "measured"
    assert feed["regions"]["Italy"]["items"][0]["name"] == "Role 6"
    assert feed["regions"]["Worldwide"]["status"] == "curated"
    assert len(feed["role_observations"]) == 6
    sparse = build_pulse(_topics(), {"signals": signals[:2]}, "2026-10-14T08:00:00+00:00")
    assert sparse["regions"]["Italy"]["status"] == "curated"
    assert len(sparse["role_observations"]) == 2


def test_daily_history_is_idempotent(tmp_path):
    snap = build_pulse(_topics(), {"signals": []}, "2026-10-14T08:00:00+00:00")
    write_pulse(snap, tmp_path)
    write_pulse(snap, tmp_path)
    latest = json.loads((tmp_path / "scout/data/pulse/latest.json").read_text())
    assert latest["date"] == "2026-10-14"
    with (tmp_path / "datasets/pulse/history.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows
    assert len({(r["date"], r["kind"], r["name"], r["region"]) for r in rows}) == len(rows)
    assert all(r["measurement"] == "topic_proxy" for r in rows)


def test_landing_build_outputs_are_mirrored():
    root = Path(__file__).resolve().parents[1]
    for name in ("scout-landing.jsx", "scout-landing.js", "scout-landing.css", "scout-pulse.js"):
        assert (root / name).read_bytes() == (root / "scout" / name).read_bytes()
    for index in ("index.html", "scout/index.html"):
        text = (root / index).read_text()
        assert 'src="scout-pulse.js"' in text
        assert text.index('src="scout-pulse.js"') < text.index('src="scout-landing.js"')
