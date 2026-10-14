#!/usr/bin/env python
"""Build evidence-labeled daily landing recommendations and historical snapshots.

Only measured role signals can be described as job-posting rankings. Skills and
tools are topic-associated *proxies*, not observed job posting counts.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {
    "job_demand": 0.32, "career_value": 0.24, "github_growth": 0.18,
    "ecosystem_fit": 0.14, "project_potential": 0.12,
}
CURATED_ROLES = [
    "Developer", "Data Analyst", "Nurse", "Teacher", "Accountant",
    "Marketing Specialist", "UX/Product Designer", "Electrician",
]
TOOLS = {
    "fastapi", "langgraph", "docker", "langchain", "llamaindex",
    "opentelemetry", "kubernetes", "siem", "power bi", "tableau",
    "figma", "excel", "git", "postgresql",
}
FIELDNAMES = ["date", "region", "kind", "name", "score", "sample_size", "source", "measurement"]


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _topic_score(topic: dict) -> float:
    sig = topic.get("signals") or {}
    return round(sum(float(sig.get(k) or 0) * v for k, v in WEIGHTS.items()), 2)


def _topic_tags(topics: list[dict]) -> tuple[list[dict], list[dict]]:
    scores: dict[str, dict] = {}
    for topic in topics:
        value = _topic_score(topic)
        for name in topic.get("skills") or []:
            name = str(name).strip()
            if not name:
                continue
            key = name.casefold()
            row = scores.setdefault(key, {"name": name, "score": 0.0, "topics_count": 0})
            row["score"] += value
            row["topics_count"] += 1
    ranked = sorted(scores.values(), key=lambda r: (-r["score"], r["name"]))
    for item in ranked:
        item["score"] = round(item["score"], 2)
        item["source"] = "topic_proxy"
    tools = [dict(item) for item in ranked if item["name"].casefold() in TOOLS]
    return ranked, tools


def build_pulse(topics_doc: dict, signals_doc: dict, generated_at: str | None = None) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    skills, tools = _topic_tags(topics_doc.get("topics") or [])
    observations = []
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in signals_doc.get("signals") or []:
        if row.get("subject_kind") != "role" or not row.get("subject"):
            continue
        count = row.get("sample_size")
        if not isinstance(count, (int, float)) or count <= 0:
            continue
        region = str(row.get("region") or "Worldwide").strip()
        # The source's 'Worldwide' Adzuna query is backed by a single country;
        # it is not evidence for a globally representative labor market.
        if region.casefold() == "worldwide":
            continue
        name = str(row["subject"]).strip()
        obs = {
            "name": name, "region": region, "sample_size": int(count),
            "score": round(float(row.get("demand") or 0), 4),
            "source": str(row.get("source") or "unknown"),
            "collected_at": row.get("collected_at") or generated_at,
        }
        observations.append(obs)
        key = name.casefold()
        previous = grouped[region].get(key)
        # Avoid double-counting the same role across multiple adapters.
        if previous is None or obs["sample_size"] > previous["sample_size"]:
            grouped[region][key] = obs

    fallback = {
        "status": "curated",
        "description": "Illustrative profession suggestions; no comparable local hiring ranking.",
        "items": [{"name": name, "source": "curated"} for name in CURATED_ROLES],
    }
    regions = {"Worldwide": fallback}
    for region, by_name in sorted(grouped.items()):
        ranked = sorted(by_name.values(), key=lambda r: (-r["sample_size"], r["name"]))
        # Do not label a sparse partial sample 'top five'.
        regions[region] = (
            {"status": "measured", "description": "Ranked by observed job-posting counts in this region.",
             "items": ranked}
            if len(ranked) >= 5 else fallback
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "date": generated_at[:10],
        "regions": regions,
        "skills": skills,
        "tools": tools,
        "role_observations": observations,
        "source_status": "measured" if observations else "unavailable",
        "methodology": {
            "professions": "Region-matched observed job-posting sample sizes, or explicitly curated fallback.",
            "skills": "Sum of blended topic scores for each associated skill; not skill job-posting demand.",
            "tools": "Tool names drawn from topic-associated skills; not measured tool adoption.",
        },
    }


def write_pulse(payload: dict, root: Path = ROOT) -> None:
    folder = root / "datasets" / "pulse"
    snapshots = folder / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    (folder / "latest.json").write_text(serialized, encoding="utf-8")
    (snapshots / (payload["date"] + ".json")).write_text(serialized, encoding="utf-8")
    target = root / "scout" / "data" / "pulse" / "latest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized, encoding="utf-8")

    # Rebuild from dated snapshots so reruns replace a day's rows (idempotent).
    rows = []
    for path in sorted(snapshots.glob("????-??-??.json")):
        snap = _read(path)
        date = snap.get("date", path.stem)
        for obs in snap.get("role_observations") or []:
            rows.append({
                "date": date, "region": obs.get("region", ""),
                "kind": "profession", "name": obs.get("name", ""),
                "score": obs.get("score", ""), "sample_size": obs.get("sample_size", ""),
                "source": obs.get("source", ""), "measurement": "job_postings",
            })
        for kind in ("skills", "tools"):
            for item in snap.get(kind) or []:
                rows.append({
                    "date": date, "region": "Worldwide", "kind": kind[:-1],
                    "name": item["name"], "score": item["score"],
                    "sample_size": "", "source": "scout_topics", "measurement": "topic_proxy",
                })
    with (folder / "history.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    data = build_pulse(
        _read(args.root / "datasets" / "latest.json"),
        _read(args.root / "datasets" / "signals" / "latest.json"),
    )
    write_pulse(data, args.root)
    print(f"Published Scout Pulse {data['date']} ({len(data['role_observations'])} observed roles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
