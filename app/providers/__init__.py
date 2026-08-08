"""Learning-resource provider adapters (spec section 6).

Every provider implements the same :class:`LearningResourceProvider` protocol so
the ranker and optimizer never care where a resource came from. Structured,
official sources are preferred; web-search discovery (Udemy, Coursera) is stored
only as provenance-tagged candidates that redirect the user to the provider.
"""
from app.providers.base import (
    LearningResourceProvider,
    available_providers,
    provider_health,
    search_all,
)

__all__ = [
    "LearningResourceProvider",
    "available_providers",
    "provider_health",
    "search_all",
]
