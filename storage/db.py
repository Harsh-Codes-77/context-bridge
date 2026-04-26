"""SQLite storage layer for context-bridge.

This module stores branch session data and short-lived integration caches
in a local database under the user's home directory.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# Database location requested by the spec: ~/.context-bridge/data.db
DB_DIR = Path.home() / ".context-bridge"
DB_PATH = DB_DIR / "data.db"


def _utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_utc(value: str) -> datetime:
    """Parse ISO datetime and normalize to UTC-aware datetime."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_connection() -> sqlite3.Connection:
    """Create DB folder if needed and return a SQLite connection."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create required tables and indexes if they do not already exist."""
    with _get_connection() as conn:
        # One latest session row per branch. We update this row on save_session.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_name TEXT NOT NULL UNIQUE,
                repo TEXT NOT NULL,
                last_active TEXT NOT NULL,
                files_touched TEXT NOT NULL,
                notes TEXT
            )
            """
        )

        # One latest cache row per (branch, data_type). save_cache upserts this.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS context_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                content TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                UNIQUE(branch_name, data_type)
            )
            """
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_branch_type ON context_cache(branch_name, data_type)"
        )
        conn.commit()


def save_session(branch: str, repo: str, files: list[str]) -> None:
    """Save or update the latest session details for a branch.

    Args:
        branch: Git branch name.
        repo: Repository in owner/name format.
        files: List of touched file paths.
    """
    if not branch.strip():
        raise ValueError("branch must not be empty")
    if not repo.strip():
        raise ValueError("repo must not be empty")

    init_db()
    now_iso = _utc_now_iso()
    files_json = json.dumps(files or [])

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (branch_name, repo, last_active, files_touched, notes)
            VALUES (?, ?, ?, ?, '')
            ON CONFLICT(branch_name) DO UPDATE SET
                repo = excluded.repo,
                last_active = excluded.last_active,
                files_touched = excluded.files_touched
            """,
            (branch.strip(), repo.strip(), now_iso, files_json),
        )
        conn.commit()


def get_last_session(branch: str) -> dict[str, Any] | None:
    """Return the latest session record for a branch, or None if missing."""
    if not branch.strip():
        raise ValueError("branch must not be empty")

    init_db()
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, branch_name, repo, last_active, files_touched, notes
            FROM sessions
            WHERE branch_name = ?
            ORDER BY last_active DESC
            LIMIT 1
            """,
            (branch.strip(),),
        ).fetchone()

    if row is None:
        return None

    try:
        files = json.loads(row["files_touched"])
    except (TypeError, json.JSONDecodeError):
        files = []

    return {
        "id": row["id"],
        "branch_name": row["branch_name"],
        "repo": row["repo"],
        "last_active": row["last_active"],
        "files_touched": files,
        "notes": row["notes"],
    }


def save_cache(branch: str, data_type: str, content: Any) -> None:
    """Save or update cached integration data for a branch/data_type pair."""
    if not branch.strip():
        raise ValueError("branch must not be empty")
    if not data_type.strip():
        raise ValueError("data_type must not be empty")

    init_db()
    now_iso = _utc_now_iso()
    content_json = json.dumps(content)

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO context_cache (branch_name, data_type, content, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(branch_name, data_type) DO UPDATE SET
                content = excluded.content,
                fetched_at = excluded.fetched_at
            """,
            (branch.strip(), data_type.strip(), content_json, now_iso),
        )
        conn.commit()


def get_cache(branch: str, data_type: str, max_age_minutes: int = 30) -> Any | None:
    """Return cached data if fresh enough; otherwise return None.

    Args:
        branch: Git branch name.
        data_type: Cache category such as github/slack/linear.
        max_age_minutes: Maximum accepted cache age.
    """
    if not branch.strip():
        raise ValueError("branch must not be empty")
    if not data_type.strip():
        raise ValueError("data_type must not be empty")
    if max_age_minutes < 0:
        raise ValueError("max_age_minutes must be >= 0")

    entry = get_cache_with_meta(branch, data_type, max_age_minutes=max_age_minutes)
    if not entry:
        return None
    if not entry["is_fresh"]:
        return None
    return entry["content"]


def get_cache_with_meta(
    branch: str,
    data_type: str,
    max_age_minutes: int | None = 30,
) -> dict[str, Any] | None:
    """Return cached content and metadata for a branch/data_type pair.

    Args:
        branch: Git branch name.
        data_type: Cache category such as github/slack/linear.
        max_age_minutes: Optional freshness threshold. If None, freshness is not enforced.
    """
    if not branch.strip():
        raise ValueError("branch must not be empty")
    if not data_type.strip():
        raise ValueError("data_type must not be empty")
    if max_age_minutes is not None and max_age_minutes < 0:
        raise ValueError("max_age_minutes must be >= 0 when provided")

    init_db()
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT content, fetched_at
            FROM context_cache
            WHERE branch_name = ? AND data_type = ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (branch.strip(), data_type.strip()),
        ).fetchone()

    if row is None:
        return None

    try:
        content = json.loads(row["content"])
    except (TypeError, json.JSONDecodeError):
        return None

    fetched_at = _parse_iso_utc(row["fetched_at"])
    age = datetime.now(timezone.utc) - fetched_at
    is_fresh = True
    if max_age_minutes is not None:
        is_fresh = age <= timedelta(minutes=max_age_minutes)

    return {
        "content": content,
        "fetched_at": row["fetched_at"],
        "age_minutes": round(age.total_seconds() / 60, 2),
        "is_fresh": is_fresh,
    }


def get_all_sessions() -> list[dict[str, Any]]:
    """Return all sessions ordered by most recent activity first."""
    init_db()
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, branch_name, repo, last_active, files_touched, notes
            FROM sessions
            ORDER BY last_active DESC
            """
        ).fetchall()

    sessions: list[dict[str, Any]] = []
    for row in rows:
        try:
            files = json.loads(row["files_touched"])
        except (TypeError, json.JSONDecodeError):
            files = []

        sessions.append(
            {
                "id": row["id"],
                "branch_name": row["branch_name"],
                "repo": row["repo"],
                "last_active": row["last_active"],
                "files_touched": files,
                "notes": row["notes"],
            }
        )

    return sessions


if __name__ == "__main__":
    init_db()
    print("DB initialized successfully")