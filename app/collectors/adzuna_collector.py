"""Adzuna job-postings adapter (Scout 2.0 Phase 3).

Adzuna publishes an openly-documented Jobs API with a generous free tier. We use
two lightweight endpoints:

  * ``/search``  — count of live postings for a query (the demand measure).
  * ``/history`` — average-salary / posting history, used only as extra context.

Design constraints (see docs/SCOUT_RADAR_PLAN.md):
  * **Fail-safe.** Any network / parse / auth error yields ``[]`` — never an
    exception that could break the nightly collect job.
  * **Keyless → skip.** Without ``ADZUNA_APP_ID`` + ``ADZUNA_APP_KEY`` the
    adapter returns ``[]`` immediately, so the pipeline degrades cleanly.
  * **No fabrication.** Measures come from the reported ``count``; if Adzuna
    reports nothing we emit nothing.

Adzuna country codes are ISO-ish two-letter slugs (gb, us, de, ...). We map a
handful of common country labels; unknown labels fall back to ``gb`` (Adzuna's
default catalog) so a query still resolves.
"""
from __future__ import annotations

import os

import requests

from app.collectors.signal import Evidence, Signal

ADZUNA_API = "https://api.adzuna.com/v1/api"
DEFAULT_TIMEOUT = 20

# Country label -> Adzuna country code. Adzuna only covers a subset of markets;
# anything not listed maps to the widest catalog (gb) so the query still works.
_COUNTRY_CODES = {
    "worldwide": "gb",
    "united kingdom": "gb",
    "uk": "gb",
    "england": "gb",
    "united states": "us",
    "usa": "us",
    "us": "us",
    "germany": "de",
    "deutschland": "de",
    "france": "fr",
    "italy": "it",
    "italia": "it",
    "spain": "es",
    "netherlands": "nl",
    "poland": "pl",
    "canada": "ca",
    "australia": "au",
    "india": "in",
    "brazil": "br",
    "brasil": "br",
    "singapore": "sg",
    "austria": "at",
    "switzerland": "ch",
    "belgium": "be",
    "mexico": "mx",
    "south africa": "za",
    "new zealand": "nz",
}

# Normalization: Adzuna posting counts span roughly 0..50k for a broad role in a
# large market. We compress with a soft cap so "demand" stays comparable in
# [0, 1] across markets without a country-by-country baseline.
_DEMAND_CAP = 20000


def _country_code(country: str | None) -> str:
    if not country:
        return "gb"
    return _COUNTRY_CODES.get(country.strip().lower(), "gb")


def _credentials() -> tuple[str, str] | None:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if app_id and app_key:
        return app_id, app_key
    return None


def _demand_from_count(count: int) -> float:
    if count <= 0:
        return 0.0
    # Log-ish soft compression: reaches ~0.9 near the cap, never exceeds 1.0.
    ratio = min(count, _DEMAND_CAP) / _DEMAND_CAP
    return round(min(1.0, 0.15 + 0.85 * ratio), 4)


def search_postings(
    role: str,
    country: str | None = None,
    city: str | None = None,
    *,
    session: requests.Session | None = None,
) -> dict | None:
    """Return the raw Adzuna ``/search`` payload for a role, or ``None``.

    Returns ``None`` (not ``{}``) when the adapter is unconfigured or the call
    fails, so callers can distinguish "no data" from "zero postings".
    """
    creds = _credentials()
    if not creds:
        return None
    app_id, app_key = creds
    code = _country_code(country)
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 1,
        "what": role,
        "content-type": "application/json",
    }
    if city:
        params["where"] = city
    url = f"{ADZUNA_API}/jobs/{code}/search/1"
    http = session or requests
    try:
        resp = http.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def collect_role_signals(
    roles: list[str],
    *,
    domain: str = "tech-data",
    country: str | None = None,
    city: str | None = None,
    session: requests.Session | None = None,
) -> list[Signal]:
    """Collect one `Signal` per role from Adzuna live-posting counts.

    Fail-safe: unconfigured or unreachable Adzuna yields ``[]``. Roles that
    return zero postings are skipped (no fabricated demand).
    """
    if not _credentials():
        return []
    region = city or country
    signals: list[Signal] = []
    for role in roles:
        payload = search_postings(role, country=country, city=city, session=session)
        if not payload:
            continue
        try:
            count = int(payload.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if count <= 0:
            continue
        code = _country_code(country)
        where = f"&where={requests.utils.quote(city)}" if city else ""
        human_url = (
            f"https://www.adzuna.com/search?q={requests.utils.quote(role)}" + where
        )
        signals.append(
            Signal(
                subject=role,
                subject_kind="role",
                domain=domain,
                region=region,
                source="adzuna",
                demand=_demand_from_count(count),
                sample_size=count,
                evidence=[
                    Evidence(
                        source="adzuna",
                        title=f"{count:,} live postings for “{role}” ({code})",
                        url=human_url,
                    )
                ],
                extra={"adzuna_country": code},
            )
        )
    return signals
