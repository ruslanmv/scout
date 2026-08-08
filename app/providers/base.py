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
        try:
            for resource in provider.search(query):
                if resource.id in seen:
                    continue
                seen.add(resource.id)
                results.append(resource)
        except Exception:  # noqa: BLE001 — one bad provider must not break search
            continue
    return results
