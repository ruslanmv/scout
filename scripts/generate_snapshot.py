#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.recommender import load_topics, rank_for_location
from app.services.analysis_generator import batch_reports, DEFAULT_LOCATIONS, DEFAULT_GOALS, DEFAULT_PROFILES, topic_deep_dive
from app.services.dataset_store import write_json

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
SAMPLE = ROOT / "app/data/sample_trends.json"


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-")


def _base_dataset() -> dict[str, Any]:
    if (DATASETS / "latest.json").exists():
        return json.loads((DATASETS / "latest.json").read_text(encoding="utf-8"))
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def build_snapshot(write: bool = True) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    base = _base_dataset()
    base["generated_at"] = generated_at
    base["version"] = base.get("version", "0.1.0")
    base["workflow"] = {
        "name": "daily_scout_generation",
        "steps": [
            "collect public signals",
            "normalize topic signals",
            "rank topics globally and by location",
            "generate batch reports for goals/profiles",
            "write frontend-ready JSON files",
            "publish dataset artifacts",
        ],
        "model_policy": "Deterministic templates by default; optional ML/LLM enrichment enabled by environment variables.",
    }

    global_topics = load_topics()
    topics_by_location = {"global": global_topics}
    for loc in DEFAULT_LOCATIONS:
        country, city, slug = loc["country"], loc["city"], loc["slug"]
        topics_by_location[slug] = rank_for_location(country, city)

    batches = batch_reports(topics_by_location, goals=DEFAULT_GOALS, profiles=DEFAULT_PROFILES)

    if write:
        write_json(DATASETS / "latest.json", base)
        write_json(DATASETS / "global" / "latest.json", {"generated_at": generated_at, "scope": "global", "topics": global_topics})
        for loc in DEFAULT_LOCATIONS:
            country, city, slug = loc["country"], loc["city"], loc["slug"]
            if slug == "global":
                continue
            write_json(DATASETS / "cities" / slug / "latest.json", {"generated_at": generated_at, "country": country, "city": city, "topics": topics_by_location[slug]})
            write_json(DATASETS / "countries" / _slug(country) / "latest.json", {"generated_at": generated_at, "country": country, "topics": rank_for_location(country, None)})
        for topic in global_topics:
            tdir = DATASETS / "topics" / topic["id"]
            write_json(tdir / "latest.json", topic)
            write_json(tdir / "evidence.json", {"topic_id": topic["id"], "signals": topic.get("signals", {}), "sources": topic.get("sources", []), "trust": topic.get("trust", {})})
            write_json(tdir / "deep-dive.json", topic_deep_dive(topic, "Worldwide", None, "career", "developer"))
        write_json(DATASETS / "batches" / "latest.json", batches)
        today = datetime.now(timezone.utc).date().isoformat()
        write_json(DATASETS / "snapshots" / f"{today}.json", {"dataset": base, "batches": batches})
        write_json(DATASETS / "index.json", {
            "generated_at": generated_at,
            "latest": "latest.json",
            "batches": "batches/latest.json",
            "global": "global/latest.json",
            "snapshot": f"snapshots/{today}.json",
            "topics": [f"topics/{t['id']}/latest.json" for t in global_topics],
        })

    return {
        "generated_at": generated_at,
        "topics": len(global_topics),
        "locations": len(DEFAULT_LOCATIONS),
        "batch_reports": batches.get("batch_count", 0),
        "outputs": [
            "datasets/latest.json",
            "datasets/global/latest.json",
            "datasets/batches/latest.json",
            "datasets/snapshots/<today>.json",
            "datasets/topics/<topic>/deep-dive.json",
        ],
    }


def main():
    result = build_snapshot(write=True)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
