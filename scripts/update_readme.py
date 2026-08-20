#!/usr/bin/env python
"""Regenerate the README's "Trending now" section from the latest dataset.

Scout 2.0 / dynamic README. Every daily run rewrites the block between the
``<!-- SCOUT:TRENDS:START -->`` / ``<!-- SCOUT:TRENDS:END -->`` markers in
README.md with a premium, at-a-glance view of what's hot right now:

  1. **Top skills worldwide** — skills ranked by the blended demand of the
     topics that require them, each with a compact signal meter.
  2. **Top topics by place** — the leading topics for the seeded locations,
     from the dataset's per-place boosts.
  3. **Live job demand** — top roles by real Adzuna posting counts, shown only
     when ``datasets/signals/latest.json`` actually has signals (keyless runs
     write an empty file, so this table is simply omitted).

Trust rules mirror the rest of Scout: every number is derived from the dataset
we actually generated — nothing here is invented. When the dataset is missing,
the script leaves the existing README untouched and exits 0 (fail-safe, so a
daily job never breaks the README).

Usage::

    python scripts/update_readme.py [--readme README.md] [--check]

``--check`` renders the section and reports whether README.md is up to date
(exit 1 if it would change) without writing — useful in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path as _Path

_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
import json
from datetime import datetime, timezone

START = "<!-- SCOUT:TRENDS:START -->"
END = "<!-- SCOUT:TRENDS:END -->"

# Blend weights for a single comparable "demand" score per topic, from the
# 0-100 signal bundle. Emphasizes hiring + durable career value over raw buzz.
_BLEND = {
    "job_demand": 0.32,
    "career_value": 0.24,
    "github_growth": 0.18,
    "ecosystem_fit": 0.14,
    "project_potential": 0.12,
}

# Seeded places we surface, in display order. Keys match local_boosts entries.
_PLACES = [
    ("__worldwide__", "🌍 Worldwide"),
    ("united-states:san francisco", "🇺🇸 San Francisco"),
    ("india:bengaluru", "🇮🇳 Bengaluru"),
    ("italy:milan", "🇮🇹 Milan"),
    ("italy:rome", "🇮🇹 Rome"),
]

_METER_WIDTH = 10


def _load_json(path: _Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _topic_demand(topic: dict) -> float:
    signals = topic.get("signals", {}) or {}
    total = sum(_BLEND[k] * float(signals.get(k, 0) or 0) for k in _BLEND)
    return round(total, 1)  # 0-100 scale


def _meter(value_0_100: float) -> str:
    """A compact unicode demand meter, e.g. ``█████████░`` for 88/100."""
    filled = max(0, min(_METER_WIDTH, round(value_0_100 / 100 * _METER_WIDTH)))
    return "█" * filled + "░" * (_METER_WIDTH - filled)


def _top_skills(topics: list[dict], limit: int = 8) -> list[dict]:
    """Rank skills by the summed demand of the topics that require them."""
    acc: dict[str, dict] = {}
    for topic in topics:
        demand = _topic_demand(topic)
        for skill in topic.get("skills", []) or []:
            entry = acc.setdefault(
                skill, {"skill": skill, "weight": 0.0, "topics": [], "best": 0.0}
            )
            entry["weight"] += demand
            entry["topics"].append((demand, topic.get("name", "")))
            entry["best"] = max(entry["best"], demand)
    ranked = sorted(acc.values(), key=lambda e: (e["weight"], e["best"]), reverse=True)
    for entry in ranked:
        entry["topics"].sort(reverse=True)
        entry["driver"] = entry["topics"][0][1] if entry["topics"] else ""
        entry["count"] = len(entry["topics"])
    return ranked[:limit]


def _topics_by_place(data: dict) -> list[tuple[str, list[str]]]:
    """For each seeded place, the top topic display names by boost."""
    id_to_name = {t.get("id"): t.get("name", t.get("id")) for t in data.get("topics", [])}
    boosts = data.get("local_boosts", {}) or {}
    # Worldwide = overall demand ordering.
    worldwide = sorted(
        data.get("topics", []), key=_topic_demand, reverse=True
    )
    rows: list[tuple[str, list[str]]] = []
    for key, label in _PLACES:
        if key == "__worldwide__":
            names = [t.get("name", "") for t in worldwide[:3]]
        else:
            place = boosts.get(key, {}) or {}
            top = sorted(place.items(), key=lambda kv: kv[1], reverse=True)[:3]
            names = [id_to_name.get(tid, tid) for tid, _ in top]
        if names:
            rows.append((label, names))
    return rows


def _live_demand_rows(signals_doc: dict | None, limit: int = 6) -> list[dict]:
    """Top roles by real Adzuna posting counts, if any signals exist."""
    if not signals_doc:
        return []
    signals = signals_doc.get("signals", []) or []
    role_signals = [s for s in signals if s.get("subject_kind") == "role"]
    if not role_signals:
        return []
    # Best (highest sample_size) observation per role across regions.
    best: dict[str, dict] = {}
    for sig in role_signals:
        subj = sig.get("subject", "")
        if sig.get("sample_size", 0) >= best.get(subj, {}).get("sample_size", -1):
            best[subj] = sig
    ranked = sorted(best.values(), key=lambda s: s.get("sample_size", 0), reverse=True)
    return ranked[:limit]


def render_section(data: dict, signals_doc: dict | None) -> str:
    topics = data.get("topics", []) or []
    generated = data.get("generated_at", "")[:10] or datetime.now(timezone.utc).date().isoformat()

    lines: list[str] = [START]
    lines.append(
        "<!-- This section is regenerated every day by scripts/update_readme.py "
        "from the latest dataset. Do not edit by hand — changes here are overwritten. -->"
    )
    lines.append("## 📈 Trending now — top skills & places")
    lines.append("")
    lines.append(
        f"> Auto-generated from Scout's latest signals · **updated {generated}** · "
        f"{len(topics)} tracked topics. "
        "Demand blends job postings, career value, growth, and ecosystem fit — "
        "[how it works](docs/DATA_SOURCES.md)."
    )
    lines.append("")

    # 1. Top skills worldwide.
    skills = _top_skills(topics)
    if skills:
        lines.append("### 🔥 Top skills to learn right now")
        lines.append("")
        lines.append("| # | Skill | Demand | Driven by |")
        lines.append("| :--: | --- | :--- | --- |")
        for i, s in enumerate(skills, 1):
            # Absolute demand of the strongest topic requiring this skill (0-100),
            # so the meter is an honest reading, not a within-column ranking.
            meter_val = s["best"]
            more = f" +{s['count'] - 1} more" if s["count"] > 1 else ""
            lines.append(
                f"| {i} | **{s['skill']}** | `{_meter(meter_val)}` {int(round(meter_val))} | {s['driver']}{more} |"
            )
        lines.append("")

    # 2. Top topics by place.
    place_rows = _topics_by_place(data)
    if place_rows:
        lines.append("### 🌐 What's hot by place")
        lines.append("")
        lines.append("| Place | Leading topics |")
        lines.append("| --- | --- |")
        for label, names in place_rows:
            chips = " · ".join(names)
            lines.append(f"| {label} | {chips} |")
        lines.append("")

    # 3. Live job demand (only when real signals exist).
    live = _live_demand_rows(signals_doc)
    if live:
        lines.append("### 💼 Live job demand")
        lines.append("")
        lines.append("| Role | Domain | Region | Live postings |")
        lines.append("| --- | --- | --- | --: |")
        for s in live:
            region = s.get("region") or "Worldwide"
            postings = s.get("sample_size", 0)
            lines.append(
                f"| {s.get('subject','')} | {s.get('domain','')} | {region} | {postings:,} |"
            )
        lines.append("")
        lines.append(
            f"<sub>Source: Adzuna live job postings ({signals_doc.get('generated_at','')[:10]}).</sub>"
        )
        lines.append("")

    lines.append(
        "> 🧭 Turn any of these into a verified, ordered learning path in the "
        "**[Learning Navigator](https://ruslanmv.com/scout/scout/learn/)**."
    )
    lines.append(END)
    return "\n".join(lines)


def _replace_block(readme: str, section: str) -> str | None:
    if START not in readme or END not in readme:
        return None
    pre, rest = readme.split(START, 1)
    _, post = rest.split(END, 1)
    return pre + section + post


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the README trends section.")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--dataset", default="datasets/latest.json")
    parser.add_argument("--signals", default="datasets/signals/latest.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the README is stale; do not write.",
    )
    args = parser.parse_args()

    readme_path = _ROOT / args.readme
    data = _load_json(_ROOT / args.dataset)
    if not data or not data.get("topics"):
        print("No dataset topics found — leaving README unchanged (fail-safe).")
        return 0

    signals_doc = _load_json(_ROOT / args.signals)
    section = render_section(data, signals_doc)

    original = readme_path.read_text(encoding="utf-8")
    updated = _replace_block(original, section)
    if updated is None:
        print(
            f"Markers {START} / {END} not found in {args.readme} — nothing to do.",
            file=sys.stderr,
        )
        return 0

    if updated == original:
        print("README trends section already up to date.")
        return 0

    if args.check:
        print("README trends section is STALE (run scripts/update_readme.py).")
        return 1

    readme_path.write_text(updated, encoding="utf-8")
    print(f"Updated README trends section in {args.readme}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
