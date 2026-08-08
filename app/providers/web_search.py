"""Search-discovery adapters (Tavily / Brave, Udemy, Coursera).

Udemy discontinued its Affiliate API (Jan 2025) and Coursera's catalog needs
partner access, so Scout treats them as *search-discovery* sources: it finds
public course URLs and stores only search metadata plus provenance. It never
invents ratings, prices, duration or certificate claims — price/access display
as "Verify on provider" (spec section 6).

These adapters require a ``TAVILY_API_KEY`` or ``BRAVE_API_KEY``. Without one
they degrade cleanly: :meth:`search` returns ``[]`` and :meth:`health` reports
``disabled`` so the rest of the pipeline keeps working from the static catalog.
"""
from __future__ import annotations

import os

from app.services.learning.schemas import (
    LearningResource,
    ProviderHealth,
    ResourceAccess,
    ResourceProvenance,
    ResourceQuality,
    ResourceQuery,
    now_iso,
)


def _search_backend() -> str | None:
    if os.getenv("TAVILY_API_KEY"):
        return "tavily"
    if os.getenv("BRAVE_API_KEY"):
        return "brave"
    return None


def _run_web_search(query_text: str, limit: int) -> list[dict]:
    """Execute a site-restricted web search via Tavily or Brave.

    Returns a list of ``{title, url, snippet}`` dicts. Network calls are guarded;
    any failure yields ``[]`` so discovery never breaks the pipeline. ``httpx`` is
    imported lazily because it is an optional dependency (spec section 15).
    """
    backend = _search_backend()
    if not backend:
        return []
    try:
        import httpx  # type: ignore
    except Exception:  # noqa: BLE001 — optional dependency not installed
        return []
    try:
        if backend == "tavily":
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": os.environ["TAVILY_API_KEY"],
                    "query": query_text,
                    "max_results": limit,
                    "search_depth": "basic",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""),
                 "snippet": r.get("content", "")}
                for r in resp.json().get("results", [])
            ]
        # brave
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query_text, "count": limit},
            headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"],
                     "Accept": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""),
             "snippet": r.get("description", "")}
            for r in resp.json().get("web", {}).get("results", [])
        ]
    except Exception:  # noqa: BLE001
        return []


def _discovered_resource(provider: str, hit: dict) -> LearningResource:
    """Build a strictly-limited, provenance-tagged candidate (spec section 6).

    Only title, url and snippet are stored. Level is unknown; rating/price/
    duration are left null and surface as "Verify on provider".
    """
    url = hit.get("url", "")
    rid = f"resource:{provider}:{abs(hash(url)) % (10 ** 10)}"
    return LearningResource(
        id=rid,
        provider=provider,
        resource_type="course",
        title=hit.get("title", "").strip() or "Untitled course",
        description=(hit.get("snippet") or "").strip()[:400],
        url=url,
        level="unknown",
        skills_taught=[],
        access=ResourceAccess(type="unknown", price=None, currency=None, observed_at=None),
        quality=ResourceQuality(rating=None, rating_count=None, evidence_confidence=0.25),
        provenance=ResourceProvenance(
            source_type="web_search",
            source_url=url,
            retrieved_at=now_iso(),
            license_or_terms="Search-discovered; verify current details on provider.",
        ),
    )


class _SiteRestrictedProvider:
    """Shared logic for site-restricted course discovery."""

    provider_name = "web_search"
    site: str | None = None  # e.g. "udemy.com/course/"

    def _build_query(self, query: ResourceQuery) -> str:
        base = query.text or " ".join(query.skills)
        if self.site:
            return f'site:{self.site} "{base}"'
        return base

    def search(self, query: ResourceQuery) -> list[LearningResource]:
        if not _search_backend():
            return []
        hits = _run_web_search(self._build_query(query), max(1, min(query.limit, 10)))
        return [_discovered_resource(self.provider_name, h) for h in hits if h.get("url")]

    def health(self) -> ProviderHealth:
        backend = _search_backend()
        if not backend:
            return ProviderHealth(
                provider=self.provider_name, ok=False, mode="disabled",
                detail="No TAVILY_API_KEY or BRAVE_API_KEY configured.")
        return ProviderHealth(
            provider=self.provider_name, ok=True, mode="search",
            detail=f"Using {backend} for site-restricted discovery.")


class WebSearchProvider(_SiteRestrictedProvider):
    provider_name = "web_search"
    site = None


class UdemySearchProvider(_SiteRestrictedProvider):
    provider_name = "udemy"
    site = "udemy.com/course/"


class CourseraSearchProvider(_SiteRestrictedProvider):
    provider_name = "coursera"
    site = "coursera.org/learn/"
