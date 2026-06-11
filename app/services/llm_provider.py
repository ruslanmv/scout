"""Optional LLM enrichment provider.

Scout's daily workflow is deterministic by default. In production, operators can
turn on hosted/local language models to improve descriptions, summaries, and
project text. The API never requires these providers to be present.
"""
from __future__ import annotations

import os
from typing import Any


def provider_status() -> dict[str, Any]:
    return {
        "llm_enabled": os.getenv("SCOUT_ENABLE_LLM") == "1",
        "provider": os.getenv("SCOUT_LLM_PROVIDER", "deterministic"),
        "description_model": os.getenv("SCOUT_DESCRIPTION_MODEL", "template-v1"),
        "embedding_model": os.getenv("SCOUT_EMBEDDING_MODEL", "tf-cosine-fallback"),
        "sentence_transformers_enabled": os.getenv("SCOUT_USE_SENTENCE_TRANSFORMERS") == "1",
    }


def enrich_description(topic: dict, audience: str = "developer") -> str:
    # Placeholder adapter point for OpenAI, watsonx, Hugging Face Inference, or
    # local models. Keep deterministic output until credentials are configured.
    if os.getenv("SCOUT_ENABLE_LLM") != "1":
        return topic.get("why_follow") or topic.get("summary", "")
    # In production, route through the provider selected by SCOUT_LLM_PROVIDER.
    # This intentionally returns fallback text instead of failing daily builds.
    return topic.get("why_follow") or topic.get("summary", "")
