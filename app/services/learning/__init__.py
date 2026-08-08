"""Scout Learning Navigator — deterministic learning-path pipeline.

The most important architectural decision (spec section 22): the final learning
path is **not** generated in one LLM call. Instead a deterministic pipeline runs

    understand -> resolve goal -> skill gap -> retrieve -> normalize
    -> rank -> optimize -> (AI explain) -> validate

so that evidence, ordering and fallbacks keep the product reliable, and AI only
improves the presentation.
"""
from app.services.learning import orchestrator  # noqa: F401

__all__ = ["orchestrator"]
