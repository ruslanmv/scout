"""Runtime settings store for Scout's AI integration.

Scout talks to an OpenAI-compatible AI gateway (OllaBridge Cloud by default) to
turn collected trend signals into a real, personalized "study -> build ->
publish" path instead of a hardcoded template.

Settings come from two layers, merged in this order:

1. Environment variables (the deployment default — the "credentials as
   environment variables" the operator configures once).
2. Runtime overrides saved by an admin from the Settings page, persisted to a
   small JSON file so they survive restarts without a redeploy.

The admin key itself is intentionally **only** read from the environment
(`SCOUT_ADMIN_KEY`) so the UI can never lock the operator out or rotate its own
gate. Secrets (the API key) are stored but never returned to the browser in
full — callers get a masked hint instead.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any

# Public OllaBridge Cloud gateway. Works out of the box with the `free-best`
# routing alias and no API key. Admins can point this at their own gateway and
# other aliases (free-fast, qwen2.5:1.5b, fable-5, claude-best, ...).
DEFAULT_BASE_URL = "https://ruslanmv-ollabridge.hf.space/v1"
DEFAULT_MODEL = "free-best"
DEFAULT_PROVIDER = "OllaBridge Cloud"

# Fields an admin may override at runtime. Everything else stays env-only.
_OVERRIDABLE = {
    "ai_enabled",
    "ai_provider",
    "ai_base_url",
    "ai_model",
    "ai_api_key",
    "ai_temperature",
    "ai_timeout",
    "ai_max_tokens",
}

_lock = threading.Lock()


def _config_path() -> Path:
    return Path(os.getenv("SCOUT_RUNTIME_CONFIG", "runtime/settings.json"))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default


def _defaults_from_env() -> dict[str, Any]:
    return {
        "ai_enabled": _env_bool("SCOUT_AI_ENABLED", True),
        "ai_provider": os.getenv("SCOUT_AI_PROVIDER", DEFAULT_PROVIDER),
        "ai_base_url": os.getenv("SCOUT_AI_BASE_URL", DEFAULT_BASE_URL),
        "ai_model": os.getenv("SCOUT_AI_MODEL", DEFAULT_MODEL),
        "ai_api_key": os.getenv("SCOUT_AI_API_KEY", ""),
        "ai_temperature": _env_float("SCOUT_AI_TEMPERATURE", 0.4),
        "ai_timeout": _env_float("SCOUT_AI_TIMEOUT", 45.0),
        "ai_max_tokens": _env_int("SCOUT_AI_MAX_TOKENS", 900),
    }


def _hf_slug(part: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-")


def normalize_base_url(url: str) -> str:
    """Return a usable OpenAI-compatible base URL ending in ``/v1``.

    Accepts either the direct app endpoint or the Hugging Face Space *page* URL
    and resolves the latter to the app subdomain that actually serves the API:

        https://huggingface.co/spaces/ruslanmv/ollabridge
            -> https://ruslanmv-ollabridge.hf.space/v1
        https://ruslanmv-ollabridge.hf.space
            -> https://ruslanmv-ollabridge.hf.space/v1
        https://ruslanmv-ollabridge.hf.space/v1   (unchanged)
    """
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return DEFAULT_BASE_URL
    match = re.match(r"https?://huggingface\.co/spaces/([^/?#]+)/([^/?#]+)", raw, re.IGNORECASE)
    if match:
        raw = f"https://{_hf_slug(match.group(1))}-{_hf_slug(match.group(2))}.hf.space"
    if raw.endswith("/chat/completions") or raw.endswith("/v1"):
        return raw
    return f"{raw}/v1"


def _load_overrides() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in _OVERRIDABLE}


def get_settings() -> dict[str, Any]:
    """Full effective settings, including the raw API key. Server-side only."""
    settings = _defaults_from_env()
    settings.update(_load_overrides())
    return settings


def admin_key() -> str | None:
    """Admin gate. Env-only; if unset the admin area stays disabled."""
    key = os.getenv("SCOUT_ADMIN_KEY", "").strip()
    return key or None


def admin_enabled() -> bool:
    return admin_key() is not None


def _mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 4:
        return "•" * len(secret)
    return f"••••{secret[-4:]}"


def public_settings() -> dict[str, Any]:
    """Settings safe to send to the browser — the API key is never included."""
    s = get_settings()
    api_key = s.get("ai_api_key", "") or ""
    return {
        "ai_enabled": s["ai_enabled"],
        "ai_provider": s["ai_provider"],
        "ai_base_url": normalize_base_url(s["ai_base_url"]),
        "ai_model": s["ai_model"],
        "ai_temperature": s["ai_temperature"],
        "ai_timeout": s["ai_timeout"],
        "ai_max_tokens": s["ai_max_tokens"],
        "ai_api_key_set": bool(api_key),
        "ai_api_key_hint": _mask(api_key),
        "config_source": "runtime+env" if _load_overrides() else "env",
    }


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Apply admin overrides and persist them. Returns the masked public view.

    Only keys in ``_OVERRIDABLE`` are honored. ``ai_api_key`` is left untouched
    when omitted/None so the admin can change other fields without re-typing the
    secret; pass an empty string to explicitly clear it.
    """
    with _lock:
        overrides = _load_overrides()
        for key, value in updates.items():
            if key not in _OVERRIDABLE or value is None:
                continue
            if key == "ai_base_url" and isinstance(value, str):
                value = normalize_base_url(value)
            if key in {"ai_model", "ai_provider"} and isinstance(value, str):
                value = value.strip()
            overrides[key] = value
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(overrides, indent=2, sort_keys=True), encoding="utf-8")
    return public_settings()


def reset_overrides() -> None:
    """Remove all runtime overrides (test helper / factory reset)."""
    with _lock:
        path = _config_path()
        if path.exists():
            path.unlink()
