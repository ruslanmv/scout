"""Admin-only Settings API.

Lets the operator configure the AI provider (OllaBridge Cloud by default) at
runtime: base URL, API key, model, and an on/off switch. Defaults come from
environment variables; this just lets an admin adjust them without a redeploy.

Auth is a single shared admin key supplied via the ``SCOUT_ADMIN_KEY``
environment variable and sent on each request as the ``X-Admin-Key`` header. If
that variable is unset, the whole admin area stays disabled (locked), so a fresh
deploy is never accidentally open.
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services import ai_advisor, runtime_settings

router = APIRouter(tags=["admin"])


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    expected = runtime_settings.admin_key()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin area is disabled. Set the SCOUT_ADMIN_KEY environment variable to enable it.",
        )
    if not x_admin_key or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid admin key.")


class SettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    ai_provider: str | None = None
    ai_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_temperature: float | None = None
    ai_timeout: float | None = None
    ai_max_tokens: int | None = None


@router.get("/admin/enabled")
def admin_is_enabled():
    """Unauthenticated: lets the login screen know if admin is configured."""
    return {"enabled": runtime_settings.admin_enabled()}


@router.get("/admin/settings")
def get_settings(_: None = None, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    return {
        "settings": runtime_settings.public_settings(),
        "status": ai_advisor.ai_status(),
        "defaults": {
            "base_url": runtime_settings.DEFAULT_BASE_URL,
            "model": runtime_settings.DEFAULT_MODEL,
            "provider": runtime_settings.DEFAULT_PROVIDER,
        },
    }


@router.post("/admin/settings")
def save_settings(update: SettingsUpdate, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    runtime_settings.update_settings(update.model_dump(exclude_none=True))
    return {"saved": True, "settings": runtime_settings.public_settings()}


@router.post("/admin/test")
def test_connection(update: SettingsUpdate | None = None, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    settings = runtime_settings.get_settings()
    if update:
        # Test against the proposed values without persisting them yet.
        for key, value in update.model_dump(exclude_none=True).items():
            settings[key] = value
    return ai_advisor.test_connection(settings)


@router.post("/admin/reset")
def reset_settings(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    runtime_settings.reset_overrides()
    return {"reset": True, "settings": runtime_settings.public_settings()}
