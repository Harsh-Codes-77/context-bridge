"""Configuration helpers for API tokens.

Token loading order:
1. ~/.context-bridge/.env
2. nearest project .env (python-dotenv default search)
"""

from pathlib import Path
import os

from dotenv import load_dotenv


APP_DIR = Path.home() / ".context-bridge"
USER_ENV_PATH = APP_DIR / ".env"


def _load_env_sources() -> None:
    """Load token files with user-level env taking precedence."""
    if USER_ENV_PATH.exists():
        load_dotenv(USER_ENV_PATH, override=False)

    # Backward-compatible fallback for existing project .env files.
    load_dotenv(override=False)


def _read_env(name: str) -> str | None:
    """Read an env variable and normalize empty strings to None."""
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = _read_env(name)
    if value:
        return value

    raise RuntimeError(
        f"Missing required token: {name}. "
        "Run 'cb init' to configure tokens or add it to ~/.context-bridge/.env "
        f"(example: {name}=your_token_here)."
    )


def get_github_token() -> str:
    """Return GitHub token or raise a setup error."""
    return _require_env("GITHUB_TOKEN")


def get_linear_token() -> str:
    """Return Linear token or raise a setup error."""
    return _require_env("LINEAR_TOKEN")


def get_slack_token() -> str:
    """Return Slack token or raise a setup error."""
    return _require_env("SLACK_TOKEN")


_load_env_sources()

# Backward-compatible constants for existing imports.
GITHUB_TOKEN = _read_env("GITHUB_TOKEN")
LINEAR_TOKEN = _read_env("LINEAR_TOKEN")
SLACK_TOKEN = _read_env("SLACK_TOKEN")