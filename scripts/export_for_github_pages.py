#!/usr/bin/env python
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ensure_latest_dataset() -> Path:
    latest = ROOT / "datasets" / "latest.json"
    if latest.exists():
        return latest
    from scripts.generate_snapshot import main as generate_snapshot

    generate_snapshot()
    if not latest.exists():
        raise FileNotFoundError("datasets/latest.json was not generated")
    return latest


def _copy_site(src: Path, out: Path, latest: Path, index: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(src, out, dirs_exist_ok=True)
    data_dir = out / "data"
    data_dir.mkdir(exist_ok=True)
    shutil.copy2(latest, data_dir / "latest.json")
    if index.exists():
        shutil.copy2(index, data_dir / "index.json")
    else:
        (data_dir / "index.json").write_text(json.dumps({"latest": "latest.json"}, indent=2), encoding="utf-8")


def copy_dashboard(out: Path, latest: Path, index: Path) -> None:
    _copy_site(ROOT / "dashboard", out, latest, index)


def copy_scout(out: Path, latest: Path, index: Path) -> None:
    """Regenerate and export the multi-page Scout product to /scout."""
    from scripts.build_scout_site import main as build_scout_site

    build_scout_site()
    _copy_site(ROOT / "scout", out, latest, index)


def main() -> None:
    public = ROOT / "public"
    latest = ensure_latest_dataset()
    index = ROOT / "datasets" / "index.json"
    if public.exists():
        shutil.rmtree(public)
    copy_dashboard(public, latest, index)
    copy_scout(public / "scout", latest, index)
    (public / "404.html").write_text((public / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    # Serve the bundle as-is: no Jekyll build (so folders like assets/ and any
    # underscore-prefixed paths are published untouched, and README is never
    # rendered in place of the app).
    (public / ".nojekyll").write_text("", encoding="utf-8")
    # Preserve the latest source-health snapshot alongside the site.
    health = ROOT / "datasets" / "health" / "latest.json"
    if health.exists():
        shutil.copy2(health, public / "health.json")

    # Ship the nightly AI-batch plans so the static site can serve real AI output
    # from the dataset (Scout 2.0 §6). Mirrored under both site roots.
    ai_plans = ROOT / "datasets" / "ai_plans"
    if ai_plans.exists():
        for dest in (public / "data" / "ai_plans", public / "scout" / "data" / "ai_plans"):
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ai_plans, dest, dirs_exist_ok=True)

    # Ship the latest universal demand signals (Scout 2.0 Phase 3) so the static
    # site and any client can read job-market demand without the backend.
    signals = ROOT / "datasets" / "signals" / "latest.json"
    if signals.exists():
        for dest in (public / "data", public / "scout" / "data"):
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(signals, dest / "signals.json")
    print(f"Exported GitHub Pages bundle to {public} and {public / 'scout'}")


if __name__ == "__main__":
    main()
