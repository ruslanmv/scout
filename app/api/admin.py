"""Admin-only Settings API.

Lets the operator configure the AI provider (OllaBridge Cloud by default) at
runtime: base URL, API key, model, and an on/off switch. Defaults come from
environment variables; this just lets an admin adjust them without a redeploy.

On a fresh install the owner creates a password once; only its salted hash is
stored. ``SCOUT_ADMIN_KEY`` remains a backwards-compatible bootstrap option.
The credential is sent on each request as the ``X-Admin-Key`` header.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services import ai_advisor, runtime_settings

router = APIRouter(tags=["admin"])


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not runtime_settings.admin_enabled():
        raise HTTPException(
            status_code=503,
            detail="Admin setup is required. Open /dashboard/admin.html to create the first password.",
        )
    if not runtime_settings.verify_admin_password(x_admin_key):
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


class PasswordRequest(BaseModel):
    password: str


@router.get("/admin/enabled")
def admin_is_enabled():
    """Unauthenticated: lets the login screen know if admin is configured."""
    enabled = runtime_settings.admin_enabled()
    return {"enabled": enabled, "setup_required": not enabled}


@router.post("/admin/setup", status_code=201)
def initial_setup(request: PasswordRequest):
    """Create the administrator exactly once on a fresh installation."""
    try:
        runtime_settings.set_admin_password(request.password, initial=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"created": True}


@router.post("/admin/password")
def change_password(request: PasswordRequest, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    try:
        runtime_settings.set_admin_password(request.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"changed": True}


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
