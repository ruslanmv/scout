"""Source & API health monitor.

Scout depends on external data sources (GitHub, Hugging Face), an AI gateway,
course providers (Microsoft Learn, Open edX, YouTube), search-discovery
providers (Tavily, Brave) and the individual course URLs it recommends. This
module checks that all of them are reachable — and, crucially, that recommended
**course URLs are still available each day** — so maintainers always know when a
source breaks and needs a fix.

Design principles, consistent with the rest of Scout:

* **Fail-safe.** A probe never raises; every target resolves to a status
  (``up`` / ``degraded`` / ``down`` / ``skipped`` / ``unknown``).
* **Injectable.** The HTTP probe is a parameter, so tests run without a network
  and the daily job can swap in a bounded, parallel checker.
* **Snapshotted.** Results are written to ``datasets/health/`` with timestamps,
  giving an auditable daily history (the same pattern as trend datasets).
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.config import settings

# A probe returns (http_status | None, latency_ms | None, error | None).
ProbeResult = tuple[int | None, float | None, str | None]
Probe = Callable[[str], ProbeResult]

_UA = "ScoutHealthBot/1.0 (+https://github.com/ruslanmv/scout)"
DEFAULT_TIMEOUT = 8.0

# Statuses we treat as "reachable and fine".
_OK = {200, 201, 202, 204, 301, 302, 303, 307, 308}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def health_dir() -> Path:
    return Path(settings.scout_data_dir) / "health"


# --- Registry of monitored APIs & sources -----------------------------------
# ``requires_key`` marks a target that is skipped (not failed) when its API key
# is absent — an unconfigured optional provider is not "down".

def _api_targets() -> list[dict[str, Any]]:
    from app.services import runtime_settings

    ai_base = runtime_settings.normalize_base_url(
        runtime_settings.get_settings().get("ai_base_url", ""))
    return [
        {"name": "GitHub API", "category": "signal_source", "url": "https://api.github.com",
         "role": "developer activity signals"},
        {"name": "Hugging Face API", "category": "signal_source",
         "url": "https://huggingface.co/api/models?limit=1", "role": "AI builder activity signals"},
        {"name": "OllaBridge AI gateway", "category": "ai_gateway",
         "url": (ai_base.rstrip("/") + "/models") if ai_base
                else "https://ruslanmv-ollabridge.hf.space/v1/models",
         "role": "live AI plan narration"},
        {"name": "Microsoft Learn", "category": "course_provider",
         "url": "https://learn.microsoft.com/en-us/training/", "role": "official training & certs"},
        {"name": "Open edX (edx.org)", "category": "course_provider",
         "url": "https://www.edx.org/", "role": "structured course catalog",
         "note": "anonymous catalog API is installation-gated; we check host liveness"},
        {"name": "YouTube Data API", "category": "course_provider",
         "url": "https://www.googleapis.com/youtube/v3/videos", "requires_key": "YOUTUBE_API_KEY",
         "role": "video course discovery"},
        {"name": "Tavily Search", "category": "search_provider", "url": "https://api.tavily.com",
         "requires_key": "TAVILY_API_KEY", "role": "AI course discovery"},
        {"name": "Brave Search", "category": "search_provider",
         "url": "https://api.search.brave.com/res/v1/web/search", "requires_key": "BRAVE_API_KEY",
         "role": "site-restricted course discovery"},
    ]


def _course_url_targets() -> list[dict[str, Any]]:
    """The individual course/resource URLs Scout recommends, plus certification
    pages — so we detect the day a recommended course or blueprint disappears."""
    from app.providers.static_catalog import StaticCatalogProvider
    from app.services.learning import certifications
    from app.services.learning.schemas import ResourceQuery

    targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in StaticCatalogProvider().search(ResourceQuery(limit=200)):
        if r.url and r.url not in seen:
            seen.add(r.url)
            targets.append({"name": r.title, "category": "course_url", "url": r.url,
                            "role": f"resource · {r.provider}"})
    for c in certifications.all_certifications():
        if c.official_url and c.official_url not in seen:
            seen.add(c.official_url)
            targets.append({"name": c.name, "category": "certification", "url": c.official_url,
                            "role": f"official blueprint · {c.issuer}"})
    return targets


def monitored_targets(include_courses: bool = True) -> list[dict[str, Any]]:
    targets = _api_targets()
    if include_courses:
        targets += _course_url_targets()
    return targets


# --- HTTP probe -------------------------------------------------------------

def requests_probe(url: str, timeout: float = DEFAULT_TIMEOUT) -> ProbeResult:
    """Default probe using ``requests`` (already a Scout dependency).

    A GET (streamed, so we never download a whole page) with a browser-like
    User-Agent, following redirects. Returns ``(status, latency_ms, error)`` and
    never raises — connection/timeout errors come back as ``error``.
    """
    import requests  # local import keeps this module import-cheap

    started = datetime.now(timezone.utc)
    try:
        resp = requests.get(
            url, timeout=timeout, stream=True, allow_redirects=True,
            headers={"User-Agent": _UA, "Accept": "*/*"},
        )
        latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        status = resp.status_code
        resp.close()
        return status, round(latency), None
    except Exception as exc:  # noqa: BLE001 — classify, never raise
        return None, None, f"{type(exc).__name__}: {str(exc)[:120]}"


def classify(target: dict[str, Any], status: int | None, error: str | None) -> tuple[str, str]:
    """Map a probe result to a (status, detail) pair.

    Course URLs are strict about 404/410 (the resource is gone). Auth-required
    APIs treat 401/403 as reachable (host is up), and 429 as rate-limited.
    """
    if error:
        return "down", error
    if status is None:
        return "down", "no response"
    if status in _OK:
        return "up", f"HTTP {status}"
    if status in (401, 403):
        return "up", f"HTTP {status} — reachable, auth required"
    if status == 429:
        return "degraded", "HTTP 429 — rate limited"
    if status in (404, 410):
        # A missing course/blueprint is a real availability problem (the resource
        # is gone). On an API base a 404 more likely means the path moved — worth
        # a look, but not a hard outage.
        if target.get("category") in ("course_url", "certification"):
            return "down", f"HTTP {status} — resource not found"
        return "degraded", f"HTTP {status} — endpoint may have moved"
    if 500 <= status < 600:
        return "down", f"HTTP {status} — server error"
    if 400 <= status < 500:
        return "degraded", f"HTTP {status}"
    return "degraded", f"HTTP {status}"


def _check_one(target: dict[str, Any], probe: Probe) -> dict[str, Any]:
    key = target.get("requires_key")
    base = {
        "name": target["name"], "category": target["category"], "url": target["url"],
        "role": target.get("role", ""), "checked_at": _now(),
    }
    if key and not os.getenv(key):
        return {**base, "status": "skipped", "http_status": None, "latency_ms": None,
                "detail": f"no {key} configured — provider disabled"}
    status_code, latency, error = probe(target["url"])
    status, detail = classify(target, status_code, error)
    return {**base, "status": status, "http_status": status_code,
            "latency_ms": latency, "detail": detail}


# --- Aggregation ------------------------------------------------------------

def _overall(counts: dict[str, int]) -> str:
    if counts.get("down"):
        return "down"
    if counts.get("degraded"):
        return "degraded"
    if counts.get("up"):
        return "up"
    return "unknown"


def run_health_check(
    *,
    probe: Probe | bool = True,
    include_courses: bool = True,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Probe every monitored target and return an aggregated snapshot.

    ``probe`` may be a callable (custom/fake probe) or a bool: ``True`` uses the
    default network probe, ``False`` returns a config-only snapshot (no network),
    marking network targets ``unknown`` — handy for a fast, side-effect-free API
    response when no cached snapshot exists.
    """
    targets = monitored_targets(include_courses)

    if probe is False:
        checks = []
        for t in targets:
            key = t.get("requires_key")
            if key and not os.getenv(key):
                st, detail = "skipped", f"no {key} configured"
            else:
                st, detail = "unknown", "not probed (config-only)"
            checks.append({"name": t["name"], "category": t["category"], "url": t["url"],
                           "role": t.get("role", ""), "status": st, "http_status": None,
                           "latency_ms": None, "detail": detail, "checked_at": _now()})
    else:
        probe_fn: Probe = requests_probe if probe is True else probe
        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
            checks = list(pool.map(lambda t: _check_one(t, probe_fn), targets))

    counts: dict[str, int] = {}
    by_category: dict[str, dict[str, int]] = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
        cat = by_category.setdefault(c["category"], {})
        cat[c["status"]] = cat.get(c["status"], 0) + 1

    # Learning-provider self-reports (static catalog, search adapters).
    try:
        from app.providers import base as providers
        provider_health = [h.model_dump() for h in providers.provider_health()]
    except Exception:  # noqa: BLE001
        provider_health = []

    return {
        "generated_at": _now(),
        "overall": _overall(counts),
        "counts": counts,
        "by_category": by_category,
        "checks": checks,
        "provider_health": provider_health,
    }


# --- Snapshot persistence ---------------------------------------------------

def save_snapshot(snapshot: dict[str, Any], directory: Path | None = None) -> dict[str, str]:
    directory = directory or health_dir()
    directory.mkdir(parents=True, exist_ok=True)
    day = snapshot.get("generated_at", _now())[:10]
    latest = directory / "latest.json"
    dated = directory / f"{day}.json"
    payload = json.dumps(snapshot, indent=2, ensure_ascii=False)
    latest.write_text(payload, encoding="utf-8")
    dated.write_text(payload, encoding="utf-8")
    return {"latest": str(latest), "dated": str(dated)}


def load_latest_snapshot(directory: Path | None = None) -> dict[str, Any] | None:
    directory = directory or health_dir()
    latest = directory / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def get_health(*, live: bool = False) -> dict[str, Any]:
    """Health for the API: the cached daily snapshot by default (fast), or a
    fresh live probe when ``live`` is set. Falls back to a config-only snapshot
    when nothing is cached, so the endpoint always returns something useful.
    """
    if live:
        snap = run_health_check(probe=True)
        snap["source"] = "live"
        return snap
    cached = load_latest_snapshot()
    if cached:
        cached["source"] = "cached_snapshot"
        return cached
    snap = run_health_check(probe=False)
    snap["source"] = "config_only"
    return snap
