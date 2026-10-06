"""Configuration loading.

This is the only module allowed to touch environment variables. Keeping the
lookup in one place means a lesson never repeats `os.environ[...]` and a
reviewer can answer "where does config come from?" by reading one file.

`.env` support is optional. If python-dotenv is not installed the module still
works, which keeps the lessons runnable with zero third-party dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = REPO_ROOT / ".env"
RUNS_DIR = REPO_ROOT / ".runs"

_ENV_LOADED = False


def load_env() -> bool:
    """Load `.env` into the process environment once. Returns True if a file was read."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return False
    _ENV_LOADED = True
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return False
    return bool(load_dotenv(DOTENV_PATH))


def env_str(name: str, default: str = "") -> str:
    load_env()
    value = os.environ.get(name, "").strip()
    return value or default


def env_int(name: str, default: int) -> int:
    raw = env_str(name)
    try:
        return int(raw)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    raw = env_str(name)
    try:
        return float(raw)
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    raw = env_str(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def env_api_key(name: str) -> str | None:
    """Return an API key only when it is non-empty. Never logged, never echoed."""
    load_env()
    value = os.environ.get(name, "").strip()
    return value or None


def model_name(default: str = "echo") -> str:
    return env_str("AGENT_MODEL_NAME", default)


def max_steps(default: int = 8) -> int:
    return env_int("AGENT_MAX_STEPS", default)


def require_approval(default: bool = True) -> bool:
    return env_bool("AGENT_REQUIRE_APPROVAL", default)