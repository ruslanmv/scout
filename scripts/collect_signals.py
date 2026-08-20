#!/usr/bin/env python
"""Collect universal demand signals into ``datasets/signals/latest.json``.

Scout 2.0 Phase 3. Walks the occupation taxonomy across every domain and asks
each configured collector (currently Adzuna job postings) for live demand. The
output is a flat list of normalized `Signal`s the recommender and the dynamic
README can consume without knowing which adapter produced them.

Fail-safe by design: with no ``ADZUNA_APP_ID`` / ``ADZUNA_APP_KEY`` the run
still succeeds and writes a valid file with an empty ``signals`` list and a note,
so the daily workflow never fails just because a source is unconfigured.

Usage::

    python scripts/collect_signals.py [--out datasets/signals] \
        [--countries Worldwide,United States,Germany] [--max-roles 0]
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

from app.collectors import adzuna_collector
from app.collectors.signal import Signal
from app.services.learning import taxonomy

# Countries we sweep by default. Adzuna covers a subset; unknown labels degrade
# to its widest catalog inside the adapter, so this list is safe to extend.
DEFAULT_COUNTRIES = ["Worldwide", "United States", "United Kingdom", "Germany", "India"]


def _roles_by_domain() -> dict[str, list[str]]:
    """Group occupation display names by domain from the taxonomy."""
    grouped: dict[str, list[str]] = {}
    for occ in taxonomy.all_occupations():
        if not occ.domain:
            continue
        grouped.setdefault(occ.domain, []).append(occ.name)
    return grouped


def collect(countries: list[str], max_roles: int = 0) -> list[Signal]:
    """Collect signals across all domains × countries. Adapters fail safe."""
    roles_by_domain = _roles_by_domain()
    merged: dict[str, Signal] = {}
    for country in countries:
        region_country = None if country.lower() == "worldwide" else country
        for domain, roles in roles_by_domain.items():
            selected = roles[:max_roles] if max_roles else roles
            signals = adzuna_collector.collect_role_signals(
                selected, domain=domain, country=region_country
            )
            for sig in signals:
                # Later runs / countries overwrite by stable key (idempotent).
                merged[sig.key()] = sig
    return list(merged.values())


def build_document(signals: list[Signal], countries: list[str]) -> dict:
    configured = adzuna_collector._credentials() is not None
    payload = [s.model_dump() for s in signals]
    domains = sorted({s.domain for s in signals})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": ["adzuna"] if configured else [],
        "countries": countries,
        "domains_covered": domains,
        "count": len(payload),
        "note": (
            "Live job-market demand from Adzuna."
            if configured
            else "No signal source configured (set ADZUNA_APP_ID / ADZUNA_APP_KEY). "
            "Frontend degrades to deterministic ranking."
        ),
        "signals": payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect universal demand signals.")
    parser.add_argument("--out", default="datasets/signals", help="Output directory.")
    parser.add_argument(
        "--countries",
        default=",".join(DEFAULT_COUNTRIES),
        help="Comma-separated country labels to sweep.",
    )
    parser.add_argument(
        "--max-roles",
        type=int,
        default=0,
        help="Cap roles per domain (0 = all). Useful to stay within API quotas.",
    )
    args = parser.parse_args()

    countries = [c.strip() for c in args.countries.split(",") if c.strip()]
    signals = collect(countries, max_roles=args.max_roles)
    doc = build_document(signals, countries)

    out_dir = _ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(
        f"Wrote {doc['count']} signals across {len(doc['domains_covered'])} domains "
        f"to {out_dir / 'latest.json'} (sources: {doc['sources'] or 'none'})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
