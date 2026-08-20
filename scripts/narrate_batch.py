#!/usr/bin/env python
"""Nightly NARRATE stage — pre-compute AI plans into the dataset (Scout 2.0 §5–6).

For each (location × goal × profile) cell it narrates the top-ranked topic(s) with
the live gateway and writes the result to ``datasets/ai_plans/<key>.json`` tagged
``source: "ai-batch"``. The static site can then serve real AI output from
yesterday's data with no live backend and no exposed key — the serving order
becomes live-AI → nightly-AI-batch → deterministic template.

Cost control: each cell carries a content hash of the inputs that determine its
plan (topic signals/rank + goal + profile + location). A cell is re-narrated only
when that hash changes, so a typical night re-runs a small fraction.

Usage:
    python scripts/narrate_batch.py                 # AI must be enabled + reachable
    python scripts/narrate_batch.py --top-topics 2 --max-cells 200
    python scripts/narrate_batch.py --force         # ignore hashes, re-narrate all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services import ai_advisor, runtime_settings  # noqa: E402
from app.services.analysis_generator import (  # noqa: E402
    DEFAULT_GOALS,
    DEFAULT_LOCATIONS,
    DEFAULT_PROFILES,
)
from app.services.recommender import recommend  # noqa: E402


def _load_index(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-compute AI plans into the dataset.")
    parser.add_argument("--out", default="datasets/ai_plans", help="Output directory.")
    parser.add_argument("--top-topics", type=int, default=1,
                        help="Narrate the top N topics per cell.")
    parser.add_argument("--max-cells", type=int, default=0,
                        help="Cap the number of cells narrated (0 = no cap).")
    parser.add_argument("--force", action="store_true",
                        help="Re-narrate every cell, ignoring content hashes.")
    args = parser.parse_args()

    out = (_ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.json"
    prev_index = _load_index(index_path)
    new_index: dict[str, dict] = {}

    settings = runtime_settings.get_settings()
    if not settings.get("ai_enabled"):
        print("AI is disabled (SCOUT_AI_ENABLED); nothing to narrate. "
              "Serving will use the deterministic template until AI is on.")
        # Still write an (empty/unchanged) index so downstream steps are stable.
        index_path.write_text(json.dumps({"cells": prev_index.get("cells", {}),
                                          "generated_at": ai_advisor._now(),
                                          "ai_enabled": False}, indent=2), encoding="utf-8")
        return 0

    prev_cells = prev_index.get("cells", {})
    written = skipped = failed = 0
    stop = False

    for loc in DEFAULT_LOCATIONS:
        if stop:
            break
        country, city = loc["country"], loc["city"]
        for goal in DEFAULT_GOALS:
            if stop:
                break
            for profile in DEFAULT_PROFILES:
                if stop:
                    break
                try:
                    ranked = recommend(country, city, goal, profile, max(1, args.top_topics))
                except Exception as exc:  # noqa: BLE001
                    print(f"skip cell ({country},{city},{goal},{profile}): {exc}")
                    continue
                for topic in ranked:
                    key = ai_advisor.batch_key(topic.get("id"), country, city, goal, profile)
                    chash = ai_advisor.batch_content_hash(topic, country, city, goal, profile)
                    entry = {"topic_id": topic.get("id"), "content_hash": chash,
                             "country": country, "city": city, "goal": goal, "profile": profile}
                    existing = prev_cells.get(key)
                    if (not args.force and existing and existing.get("content_hash") == chash
                            and (out / f"{key}.json").exists()):
                        new_index[key] = existing
                        skipped += 1
                        if args.max_cells and (written + skipped) >= args.max_cells:
                            stop = True
                            break
                        continue
                    plan = ai_advisor.live_plan(topic, country, city, goal, profile, settings)
                    if plan is None:
                        failed += 1
                        # keep any prior plan for this cell rather than dropping it
                        if existing:
                            new_index[key] = existing
                        continue
                    plan["source"] = "ai-batch"
                    plan["content_hash"] = chash
                    plan["generated_for"] = {"country": country, "city": city,
                                             "goal": goal, "profile": profile}
                    (out / f"{key}.json").write_text(
                        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
                    entry["generated_at"] = plan["generated_at"]
                    new_index[key] = entry
                    written += 1
                    if args.max_cells and (written + skipped) >= args.max_cells:
                        stop = True
                        break

    index_path.write_text(json.dumps(
        {"cells": new_index, "generated_at": ai_advisor._now(),
         "ai_enabled": True, "count": len(new_index)}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"NARRATE done — written={written} skipped(unchanged)={skipped} "
          f"failed(ai-unreachable)={failed}; index has {len(new_index)} cells.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
