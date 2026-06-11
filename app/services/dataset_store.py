from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATASETS = ROOT / "datasets"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def latest_dataset() -> dict[str, Any]:
    return read_json(DATASETS / "latest.json", {})


def dataset_index() -> dict[str, Any]:
    snapshots = sorted((DATASETS / "snapshots").glob("*.json")) if (DATASETS / "snapshots").exists() else []
    return {
        "latest": "/api/v1/datasets/latest",
        "batches": "/api/v1/batches/latest",
        "snapshots": [p.stem for p in snapshots],
        "global": "/api/v1/trends/global",
        "locations": "/api/v1/locations",
        "topics": "/api/v1/topics",
    }


def snapshot(day: str | None = None) -> dict[str, Any] | None:
    day = day or date.today().isoformat()
    return read_json(DATASETS / "snapshots" / f"{day}.json", None)


def latest_batches() -> dict[str, Any]:
    return read_json(DATASETS / "batches" / "latest.json", {"reports": [], "batch_count": 0})


def find_report(country: str, city: str | None, goal: str, profile: str) -> dict[str, Any] | None:
    data = latest_batches()
    target = {
        "country": country.lower(),
        "city": (city or "").lower(),
        "goal": goal.lower(),
        "profile": profile.lower(),
    }
    for report in data.get("reports", []):
        loc = report.get("location", {})
        if (
            str(loc.get("country", "")).lower() == target["country"]
            and str(loc.get("city") or "").lower() == target["city"]
            and str(report.get("goal", "")).lower() == target["goal"]
            and str(report.get("profile", "")).lower() == target["profile"]
        ):
            return report
    return None
