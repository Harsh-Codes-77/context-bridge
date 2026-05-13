"""Shared pytest fixtures for all tests."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database for testing.
    
    This fixture:
    - Creates a temporary SQLite DB file
    - Initializes all required tables
    - Yields the database path
    - Cleans up the file after the test completes
    
    This ensures tests don't touch the real ~/.context-bridge/data.db
    """
    # Create a temporary file
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="context_bridge_test_")
    os.close(fd)
    
    # Initialize the database with the schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_name TEXT NOT NULL UNIQUE,
            repo TEXT NOT NULL,
            last_active TEXT NOT NULL,
            files_touched TEXT NOT NULL,
            notes TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS context_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            content TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            UNIQUE(branch_name, data_type)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            full_name TEXT NOT NULL UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 0,
            added_at TEXT NOT NULL
        )
    """)
    
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cache_branch_type ON context_cache(branch_name, data_type)"
    )
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup: remove the temporary database file
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_env(monkeypatch: Any) -> dict[str, str]:
    """Set fake environment variables for testing.
    
    This fixture:
    - Sets GITHUB_TOKEN, LINEAR_TOKEN, and SLACK_TOKEN to fake values
    - Uses monkeypatch to isolate tests from real environment
    - Does not touch the real .env file
    
    Returns a dict of the set environment variables.
    """
    env_vars = {
        "GITHUB_TOKEN": "fake_github_token_123",
        "LINEAR_TOKEN": "fake_linear_token_456",
        "SLACK_TOKEN": "fake_slack_token_789",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def flask_test_client(temp_db: str, monkeypatch: Any):
    """Create a Flask test client for dashboard testing.
    
    This fixture:
    - Monkeypatches the database path to use temp_db
    - Creates a Flask app instance in testing mode
    - Returns a test client
    
    The test client uses temp_db so no real data is touched during tests.
    """
    # Patch the DB_PATH in storage.db module
    monkeypatch.setattr("storage.db.DB_PATH", Path(temp_db))
    monkeypatch.setattr("storage.db.DB_DIR", Path(temp_db).parent)
    
    # Import dashboard app after patching DB_PATH
    from dashboard.app import create_app
    
    app = create_app()
    app.config["TESTING"] = True
    
    # Override remote_addr check for testing
    with app.test_client() as client:
        # Monkeypatch _is_local_request to always return True for testing
        original_get = client.get
        
        def patched_get(path: str, **kwargs: Any):
            # Simulate localhost request
            if "environ_base" not in kwargs:
                kwargs["environ_base"] = {}
            kwargs["environ_base"]["REMOTE_ADDR"] = "127.0.0.1"
            return original_get(path, **kwargs)
        
        client.get = patched_get
        yield client


@pytest.fixture
def patched_db_path(temp_db: str, monkeypatch: Any) -> str:
    """Monkeypatch storage.db to use temp_db instead of ~/.context-bridge/data.db.
    
    This is useful for tests that directly import and call storage.db functions.
    """
    monkeypatch.setattr("storage.db.DB_PATH", Path(temp_db))
    monkeypatch.setattr("storage.db.DB_DIR", Path(temp_db).parent)
    return temp_db
