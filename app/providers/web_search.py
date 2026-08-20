"""Search-discovery adapters — real Udemy / Coursera / web courses.

Udemy discontinued its Affiliate API (Jan 2025) and Coursera's catalog needs
partner access, so Scout treats them as *search-discovery* sources: it finds
real, public course URLs via a web search and stores only title, url and a
snippet plus provenance. It never invents ratings, prices, duration or
certificate claims — price/access display as "Verify on provider" (spec §6, §17).

Three backends, in priority order (all optional, all fail-safe):

* ``TAVILY_API_KEY``  → Tavily (AI-oriented search).
* ``BRAVE_API_KEY``   → Brave (site-restricted web search).
* ``SCOUT_ENABLE_WEB_DISCOVERY=1`` → DuckDuckGo (keyless, best-effort).

With none configured, :meth:`search` returns ``[]`` and the pipeline keeps
working from the static catalog. Discovered courses are tagged with the skill
they were searched for, so the deterministic ranker can score and surface them.
"""
from __future__ import annotations

import html
import os
import re
import urllib.parse

import requests

from app.services.learning.schemas import (
    LearningResource,
    ProviderHealth,
    ResourceAccess,
    ResourceProvenance,
    ResourceQuality,
    ResourceQuery,
    now_iso,
)

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _search_backend() -> str | None:
    """Active web-search backend, or ``None`` when discovery is off."""
    if os.getenv("TAVILY_API_KEY"):
        return "tavily"
    if os.getenv("BRAVE_API_KEY"):
        return "brave"
    override = (os.getenv("SCOUT_WEB_SEARCH") or "").strip().lower()
    if override in {"duckduckgo", "ddg"}:
        return "duckduckgo"
    if _truthy("SCOUT_ENABLE_WEB_DISCOVERY"):
        return "duckduckgo"
    return None


def _tavily(query_text: str, limit: int) -> list[dict]:
    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": os.environ["TAVILY_API_KEY"], "query": query_text,
              "max_results": limit, "search_depth": "basic"},
        timeout=15.0,
    )
    resp.raise_for_status()
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in resp.json().get("results", [])]


def _brave(query_text: str, limit: int) -> list[dict]:
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query_text, "count": limit},
        headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"},
        timeout=15.0,
    )
    resp.raise_for_status()
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
            for r in resp.json().get("web", {}).get("results", [])]


def _duckduckgo(query_text: str, limit: int) -> list[dict]:
    """Keyless, best-effort HTML search. Returns [] on any block/error."""
    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query_text}, headers={"User-Agent": _UA}, timeout=15.0,
    )
    resp.raise_for_status()
    out: list[dict] = []
    for href, title in re.findall(r'result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S):
        m = re.search(r"uddg=([^&]+)", href)
        url = urllib.parse.unquote(m.group(1)) if m else href
        clean = re.sub(r"<[^>]+>", "", html.unescape(title)).strip()
        if url.startswith("http"):
            out.append({"title": clean, "url": url, "snippet": ""})
        if len(out) >= limit:
            break
    return out


def _run_web_search(query_text: str, limit: int) -> list[dict]:
    """Run a site-restricted search on the active backend. Never raises."""
    backend = _search_backend()
    if not backend:
        return []
    try:
        if backend == "tavily":
            return _tavily(query_text, limit)
        if backend == "brave":
            return _brave(query_text, limit)
        return _duckduckgo(query_text, limit)
    except Exception:  # noqa: BLE001 — discovery must never break the pipeline
        return []


def _discovered_resource(provider: str, hit: dict, skills: list[str],
                         rtype: str = "course") -> LearningResource:
    """Build a strictly-limited, provenance-tagged candidate (spec §6).

    Only title, url and snippet are stored; the resource is tagged with the
    ``skills`` it was searched for so the ranker can score it. Rating, price and
    duration stay null and surface as "Verify on provider".
    """
    url = hit.get("url", "")
    rid = f"resource:{provider}:{abs(hash(url)) % (10 ** 10)}"
    return LearningResource(
        id=rid,
        provider=provider,
        resource_type=rtype,
        title=hit.get("title", "").strip() or "Untitled course",
        description=(hit.get("snippet") or "").strip()[:400],
        url=url,
        level="unknown",
        skills_taught=list(skills),
        access=ResourceAccess(type="unknown", price=None, currency=None, observed_at=None),
        quality=ResourceQuality(rating=None, rating_count=None, evidence_confidence=0.35),
        provenance=ResourceProvenance(
            source_type="web_search",
            source_url=url,
            retrieved_at=now_iso(),
            last_verified_at=now_iso(),  # we did just observe the URL exists
            license_or_terms="Search-discovered; verify current price and details on provider.",
        ),
    )


class _SiteRestrictedProvider:
    """Shared logic for site-restricted course discovery."""

    provider_name = "web_search"
    site: str | None = None       # e.g. "udemy.com/course/"
    resource_type = "course"
    # Discovery providers must be queried per-skill (via base.web_discover), not
    # with a topic-level multi-skill query, so results are tagged with the one
    # skill they were searched for. search_all() skips them for this reason.
    discovery = True

    def _build_query(self, query: ResourceQuery) -> str:
        base = (query.text or " ".join(query.skills)).strip()
        return f'site:{self.site} "{base}"' if self.site else base

    def search(self, query: ResourceQuery) -> list[LearningResource]:
        if not _search_backend() or not (query.text or query.skills):
            return []
        hits = _run_web_search(self._build_query(query), max(1, min(query.limit, 8)))
        seen: set[str] = set()
        out: list[LearningResource] = []
        for h in hits:
            url = h.get("url", "")
            if not url or (self.site and self.site not in url) or url in seen:
                continue
            seen.add(url)
            out.append(_discovered_resource(self.provider_name, h, query.skills, self.resource_type))
        return out

    def health(self) -> ProviderHealth:
        backend = _search_backend()
        if not backend:
            return ProviderHealth(
                provider=self.provider_name, ok=False, mode="disabled",
                detail="Set TAVILY_API_KEY, BRAVE_API_KEY, or SCOUT_ENABLE_WEB_DISCOVERY=1.")
        return ProviderHealth(
            provider=self.provider_name, ok=True, mode="search",
            detail=f"Using {backend} for site-restricted course discovery.")


class WebSearchProvider(_SiteRestrictedProvider):
    provider_name = "web_search"
    site = None


class UdemySearchProvider(_SiteRestrictedProvider):
    provider_name = "udemy"
    site = "udemy.com/course/"


class CourseraSearchProvider(_SiteRestrictedProvider):
    provider_name = "coursera"
    site = "coursera.org/learn"
