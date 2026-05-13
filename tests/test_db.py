"""Tests for storage/db.py module."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from storage.db import (
    DB_PATH,
    add_repo,
    delete_session,
    get_active_repo,
    get_all_sessions,
    get_cache,
    get_last_session,
    get_notes,
    init_db,
    list_repos,
    repo_exists,
    save_cache,
    save_note,
    save_session,
    set_active_repo,
)


class TestDatabaseInitialization:
    """Tests for database table creation and initialization."""

    def test_db_initializes_tables(self, patched_db_path: str) -> None:
        """Test that init_db() creates all required tables."""
        init_db()
        
        conn = sqlite3.connect(patched_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='context_cache'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='repos'"
        )
        assert cursor.fetchone() is not None
        
        conn.close()


class TestSessionManagement:
    """Tests for session save/load/delete operations."""

    def test_save_and_get_session(self, patched_db_path: str) -> None:
        """Test saving and retrieving a session."""
        init_db()
        branch_name = "fix/CON-5"
        repo = "harsh/repo"
        files = ["auth.js", "config.py"]
        
        save_session(branch_name, repo, files)
        
        session = get_last_session(branch_name)
        assert session is not None
        assert session["branch_name"] == branch_name
        assert session["repo"] == repo
        assert session["files_touched"] == files

    def test_save_session_overwrites_previous(self, patched_db_path: str) -> None:
        """Test that saving a session twice overwrites the first one."""
        init_db()
        branch = "fix/TEST-1"
        
        save_session(branch, "owner1/repo1", ["file1.js"])
        save_session(branch, "owner2/repo2", ["file2.py"])
        
        session = get_last_session(branch)
        assert session["repo"] == "owner2/repo2"

    def test_delete_session(self, patched_db_path: str) -> None:
        """Test deleting a session."""
        init_db()
        branch = "fix/DEL-1"
        
        save_session(branch, "owner/repo", ["file.js"])
        assert get_last_session(branch) is not None
        
        delete_session(branch)
        assert get_last_session(branch) is None

    def test_get_session_nonexistent_returns_none(self, patched_db_path: str) -> None:
        """Test that getting a nonexistent session returns None."""
        init_db()
        session = get_last_session("nonexistent/branch")
        assert session is None


class TestCacheManagement:
    """Tests for cache save/load with expiration."""

    def test_save_cache_and_get_cache_within_ttl(self, patched_db_path: str) -> None:
        """Test saving and retrieving cache within TTL."""
        init_db()
        branch = "fix/CACHE-1"
        data_type = "github"
        content = {"pr": 34, "title": "Fix auth"}
        
        save_cache(branch, data_type, content)
        
        retrieved = get_cache(branch, data_type)
        assert retrieved is not None
        assert retrieved["pr"] == 34

    def test_get_cache_expired_returns_none(self, patched_db_path: str) -> None:
        """Test that expired cache is not returned."""
        init_db()
        branch = "fix/EXPIRED-1"
        data_type = "linear"
        content = {"ticket": "CON-5"}
        
        save_cache(branch, data_type, content)
        
        conn = sqlite3.connect(patched_db_path)
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=40)).isoformat()
        conn.execute(
            "UPDATE context_cache SET fetched_at = ? WHERE branch_name = ? AND data_type = ?",
            (old_time, branch, data_type)
        )
        conn.commit()
        conn.close()
        
        retrieved = get_cache(branch, data_type, max_age_minutes=30)
        assert retrieved is None

    def test_save_cache_overwrites_old_data(self, patched_db_path: str) -> None:
        """Test that saving cache with same pair overwrites old data."""
        init_db()
        branch = "fix/OVERWRITE-1"
        data_type = "slack"
        
        save_cache(branch, data_type, {"messages": 1})
        save_cache(branch, data_type, {"messages": 2})
        
        retrieved = get_cache(branch, data_type)
        assert retrieved["messages"] == 2


class TestRepoManagement:
    """Tests for repository tracking."""

    def test_add_and_list_repos(self, patched_db_path: str) -> None:
        """Test adding repos and listing them."""
        init_db()
        
        add_repo("harsh/project-1")
        add_repo("harsh/project-2")
        
        repos = list_repos()
        assert len(repos) == 2
        repo_names = [r["full_name"] for r in repos]
        assert "harsh/project-1" in repo_names
        assert "harsh/project-2" in repo_names

    def test_set_active_repo(self, patched_db_path: str) -> None:
        """Test setting a repo as active."""
        init_db()
        
        add_repo("harsh/project-1")
        add_repo("harsh/project-2")
        
        success = set_active_repo("harsh/project-2")
        assert success is True
        
        active = get_active_repo()
        assert active == "harsh/project-2"
        
        conn = sqlite3.connect(patched_db_path)
        active_count = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE is_active = 1"
        ).fetchone()[0]
        assert active_count == 1
        conn.close()

    def test_add_repo_sets_as_active(self, patched_db_path: str) -> None:
        """Test that adding a repo sets it as the active repo."""
        init_db()
        
        add_repo("owner/repo-1")
        assert get_active_repo() == "owner/repo-1"
        
        add_repo("owner/repo-2")
        assert get_active_repo() == "owner/repo-2"

    def test_set_active_repo_not_found(self, patched_db_path: str) -> None:
        """Test setting an unknown repo as active returns False."""
        init_db()
        success = set_active_repo("nonexistent/repo")
        assert success is False

    def test_repo_exists_check(self, patched_db_path: str) -> None:
        """Test checking if a repo exists."""
        init_db()
        
        add_repo("harsh/exists")
        
        assert repo_exists("harsh/exists") is True
        assert repo_exists("harsh/nonexistent") is False

    def test_list_repos_empty(self, patched_db_path: str) -> None:
        """Test listing repos when none exist."""
        init_db()
        repos = list_repos()
        assert repos == []


class TestNoteManagement:
    """Tests for session notes."""

    def test_save_and_get_notes(self, patched_db_path: str) -> None:
        """Test saving and retrieving notes for a branch."""
        init_db()
        branch = "fix/CON-5"
        note_text = "Check Redis TTL configuration"
        
        save_session(branch, "harsh/repo", ["file.js"])
        save_note(branch, note_text)
        
        notes = get_notes(branch)
        assert notes is not None and notes != ""
        assert note_text in notes

    def test_get_notes_multiple_saves(self, patched_db_path: str) -> None:
        """Test that multiple notes are accumulated."""
        init_db()
        branch = "fix/TEST-1"
        
        save_session(branch, "harsh/repo", ["file.js"])
        
        save_note(branch, "First note")
        save_note(branch, "Second note")
        
        notes = get_notes(branch)
        assert "First note" in notes
        assert "Second note" in notes

    def test_get_notes_nonexistent_returns_empty(self, patched_db_path: str) -> None:
        """Test getting notes for branch with no notes."""
        init_db()
        notes = get_notes("nonexistent/branch")
        assert notes == ""

    def test_save_note_includes_timestamp(self, patched_db_path: str) -> None:
        """Test that saved notes include a timestamp."""
        init_db()
        branch = "fix/TS-1"
        
        save_session(branch, "harsh/repo", ["file.js"])
        save_note(branch, "Timestamped note")
        
        notes = get_notes(branch)
        assert "Timestamped note" in notes
        assert "[" in notes and "]" in notes


class TestGetAllSessions:
    """Tests for retrieving all sessions."""

    def test_get_all_sessions_empty(self, patched_db_path: str) -> None:
        """Test getting all sessions when database is empty."""
        init_db()
        sessions = get_all_sessions()
        assert sessions == []

    def test_get_all_sessions_returns_all(self, patched_db_path: str) -> None:
        """Test getting all sessions returns all saved sessions."""
        init_db()
        
        save_session("fix/CON-1", "harsh/repo1", ["file1.js"])
        save_session("fix/CON-2", "harsh/repo2", ["file2.py"])
        save_session("fix/CON-3", "harsh/repo3", ["file3.go"])
        
        sessions = get_all_sessions()
        assert len(sessions) == 3
        
        branch_names = [s["branch_name"] for s in sessions]
        assert "fix/CON-1" in branch_names
        assert "fix/CON-2" in branch_names
        assert "fix/CON-3" in branch_names
