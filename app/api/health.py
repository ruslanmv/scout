from fastapi import APIRouter, Query
from datetime import datetime, timezone

from app.services import health_monitor

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness probe — is the Scout service itself up."""
    return {"status": "ok", "service": "scout", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/health/sources")
def sources_health(live: bool = Query(False, description="Probe every source now instead of "
                                      "returning the cached daily snapshot.")):
    """Health of every external source and API Scout depends on — signal sources,
    the AI gateway, course providers, and each recommended course/blueprint URL.

    Returns the cached daily snapshot by default (fast). Pass ``?live=true`` to
    probe every target right now (bounded, ~8s timeout per target).
    """
    return health_monitor.get_health(live=live)


@router.get("/health/sources/summary")
def sources_health_summary():
    """Compact health summary: overall status, counts, and any targets that are
    currently down or degraded — the "what needs a fix" view."""
    snap = health_monitor.get_health(live=False)
    attention = [
        {"name": c["name"], "category": c["category"], "status": c["status"],
         "url": c["url"], "detail": c.get("detail", "")}
        for c in snap.get("checks", []) if c["status"] in ("down", "degraded")
    ]
    return {
        "overall": snap.get("overall"),
        "generated_at": snap.get("generated_at"),
        "source": snap.get("source"),
        "counts": snap.get("counts", {}),
        "needs_attention": attention,
    }
