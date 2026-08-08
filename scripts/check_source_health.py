#!/usr/bin/env python
"""Daily source & API health check.

Probes every external source Scout depends on — signal APIs, the AI gateway,
course providers, and each recommended course/blueprint URL — and writes a
timestamped snapshot to ``datasets/health/`` (plus ``public/health.json`` for
the static site). Run by GitHub Actions on a daily schedule so maintainers are
always up to date on which sources are healthy and which need a fix.

Usage:
    python scripts/check_source_health.py
    python scripts/check_source_health.py --no-courses   # APIs only, faster
    python scripts/check_source_health.py --fail-on-down # exit non-zero if down

Exit code is 0 by default (so the workflow still commits the report). Pass
``--fail-on-down`` to make CI fail when a monitored source is down.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services import health_monitor  # noqa: E402


def _print_summary(snap: dict) -> None:
    counts = snap.get("counts", {})
    order = ["up", "degraded", "down", "skipped", "unknown"]
    line = "  ".join(f"{k}={counts.get(k, 0)}" for k in order if k in counts)
    print(f"\nSource health — overall: {snap['overall'].upper()}   ({line})")
    attention = [c for c in snap.get("checks", []) if c["status"] in ("down", "degraded")]
    if attention:
        print("\nNeeds attention:")
        for c in attention:
            print(f"  [{c['status']:>8}] {c['category']:<16} {c['name']}")
            print(f"             {c['detail']}  <{c['url']}>")
    else:
        print("\nAll monitored sources are healthy.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Scout source & API health.")
    parser.add_argument("--no-courses", action="store_true",
                        help="Skip per-course URL checks (APIs only).")
    parser.add_argument("--fail-on-down", action="store_true",
                        help="Exit non-zero if any monitored source is down.")
    parser.add_argument("--workers", type=int, default=8, help="Parallel probe workers.")
    parser.add_argument("--public", action="store_true",
                        help="Also write public/health.json for the static site.")
    args = parser.parse_args()

    snap = health_monitor.run_health_check(
        probe=True, include_courses=not args.no_courses, max_workers=args.workers)
    paths = health_monitor.save_snapshot(snap)
    print(f"wrote {paths['latest']}")
    print(f"wrote {paths['dated']}")

    if args.public:
        pub = _ROOT / "public" / "health.json"
        pub.parent.mkdir(parents=True, exist_ok=True)
        pub.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {pub}")

    _print_summary(snap)

    if args.fail_on_down and snap["overall"] == "down":
        print("\nExiting non-zero: at least one source is down.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
