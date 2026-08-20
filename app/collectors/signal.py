"""Universal signal schema (Scout 2.0 Phase 3).

Every collector — job postings, community activity, news, trends — normalizes
its raw findings into the same `Signal` shape so the recommender can rank demand
and momentum across *any* domain, not just software. A signal is always tied to
a domain and (optionally) a region, carries a small number of comparable numeric
measures in `[0, 1]`, and keeps human-checkable `evidence` links so nothing is a
black box.

Trust rules (mirroring the learning trust layer):
  * Numbers are derived from counts we actually observed, never invented.
  * When a source is keyless / unreachable, the collector returns ``[]`` — it
    never fabricates a plausible-looking signal.
  * `evidence` always points at a real URL a human can open to verify.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Evidence(BaseModel):
    """A single verifiable data point behind a signal."""

    source: str  # adapter id, e.g. "adzuna"
    title: str = ""
    url: str = ""
    observed_at: str = Field(default_factory=_utcnow_iso)


class Signal(BaseModel):
    """A normalized, cross-domain demand/momentum signal.

    `subject` is what the signal is *about* — a skill, a role, or a topic. It is
    intentionally free-text so job-market adapters (roles) and trend adapters
    (skills/topics) can both emit `Signal`s that the recommender fuses later.
    """

    subject: str
    subject_kind: str = "role"  # role | skill | topic
    domain: str = "tech-data"  # one of taxonomy.DOMAINS ids
    region: str | None = None  # country/city label, or None for worldwide

    source: str  # adapter id, e.g. "adzuna"
    # Comparable measures in [0, 1]. Absent measures stay at 0.0.
    demand: float = 0.0  # how much hiring/attention there is right now
    momentum: float = 0.0  # short-term growth vs a baseline (0.5 == flat)
    sample_size: int = 0  # raw count the measures were derived from

    evidence: list[Evidence] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
    collected_at: str = Field(default_factory=_utcnow_iso)

    def key(self) -> str:
        """Stable identity for de-duplication / merging across runs."""
        region = (self.region or "worldwide").lower()
        return f"{self.source}:{self.domain}:{region}:{self.subject.lower()}"
