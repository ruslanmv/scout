"""Provider protocol and registry.

A provider turns a :class:`ResourceQuery` into normalized
:class:`LearningResource` objects. The registry lets the orchestrator fan out a
single query across every enabled provider and merge the results.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.services.learning.schemas import (
    LearningResource,
    ProviderHealth,
    ResourceQuery,
)


@runtime_checkable
class LearningResourceProvider(Protocol):
    provider_name: str

    def search(self, query: ResourceQuery) -> list[LearningResource]:
        ...

    def health(self) -> ProviderHealth:
        ...


def _load_providers() -> list[LearningResourceProvider]:
    # Imported lazily to avoid import cycles and to keep optional network
    # adapters from being constructed unless they are actually used.
    from app.providers.static_catalog import StaticCatalogProvider
    from app.providers.web_search import (
        CourseraSearchProvider,
        UdemySearchProvider,
        WebSearchProvider,
    )

    return [
        StaticCatalogProvider(),
        WebSearchProvider(),
        UdemySearchProvider(),
        CourseraSearchProvider(),
    ]


def available_providers() -> list[LearningResourceProvider]:
    return _load_providers()


def provider_health() -> list[ProviderHealth]:
    return [p.health() for p in available_providers()]


def search_all(query: ResourceQuery) -> list[LearningResource]:
    """Fan out ``query`` to every provider, tolerating individual failures."""
    results: list[LearningResource] = []
    seen: set[str] = set()
    for provider in available_providers():
        # Discovery (search) providers are queried per-skill via web_discover so
        # their results are tagged with a single skill — never with a topic query.
        if getattr(provider, "discovery", False):
            continue
        try:
            for resource in provider.search(query):
                if resource.id in seen:
                    continue
                seen.add(resource.id)
                results.append(resource)
        except Exception:  # noqa: BLE001 — one bad provider must not break search
            continue
    return results


def web_discover(terms: list[tuple[str, str]], *, per_term: int = 2,
                 language: str = "en") -> list[LearningResource]:
    """Find real Udemy / Coursera courses for specific skills (spec §6).

    ``terms`` is a list of ``(skill_id, search_term)`` pairs. Each term is
    searched on the site-restricted providers and the results are tagged with the
    skill, so the deterministic ranker can score real courses per skill. This is a
    no-op (returns ``[]``) unless a web-search backend is configured, and every
    call is fail-safe.
    """
    from app.providers.web_search import (
        CourseraSearchProvider,
        UdemySearchProvider,
        _search_backend,
    )

    if not _search_backend() or not terms:
        return []
    providers = [UdemySearchProvider(), CourseraSearchProvider()]
    results: list[LearningResource] = []
    seen: set[str] = set()
    for skill_id, term in terms:
        for provider in providers:
            try:
                q = ResourceQuery(text=term, skills=[skill_id], language=language, limit=per_term)
                for resource in provider.search(q):
                    if resource.url in seen:
                        continue
                    seen.add(resource.url)
                    results.append(resource)
            except Exception:  # noqa: BLE001
                continue
    return results
