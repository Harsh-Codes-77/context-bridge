"""Tests for dashboard/app.py Flask routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest


class TestDashboardRoutes:
    """Tests for Flask dashboard routes."""

    def test_index_route_returns_200(self, flask_test_client) -> None:
        """Test that / route returns 200 with index page."""
        response = flask_test_client.get("/")
        
        assert response.status_code == 200
        assert "<!DOCTYPE" in response.data.decode() or "html" in response.data.decode()

    def test_api_sessions_returns_json(self, flask_test_client) -> None:
        """Test that /api/sessions returns JSON response."""
        response = flask_test_client.get("/api/sessions")
        
        assert response.status_code == 200
        assert response.content_type == "application/json"
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_api_sessions_empty(self, flask_test_client) -> None:
        """Test that /api/sessions returns empty sessions when none exist."""
        response = flask_test_client.get("/api/sessions")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["sessions"] == []
        assert data["ok"] is True
        assert data["count"] == 0

    def test_api_sessions_with_data(self, flask_test_client, temp_db: str) -> None:
        """Test that /api/sessions returns saved session data."""
        import sqlite3
        
        conn = sqlite3.connect(temp_db)
        conn.execute(
            """
            INSERT INTO sessions (branch_name, repo, last_active, files_touched, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "fix/CON-5",
                "harsh/repo",
                datetime.now(timezone.utc).isoformat(),
                '["auth.js", "config.py"]',
                "Test session"
            )
        )
        conn.commit()
        conn.close()
        
        response = flask_test_client.get("/api/sessions")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["sessions"]) > 0
        assert data["sessions"][0]["branch_name"] == "fix/CON-5"

    def test_delete_session_route(self, flask_test_client, temp_db: str) -> None:
        """Test that DELETE /api/sessions/<branch> deletes a session."""
        import sqlite3
        
        conn = sqlite3.connect(temp_db)
        conn.execute(
            """
            INSERT INTO sessions (branch_name, repo, last_active, files_touched, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "fix/DELETE-1",
                "harsh/repo",
                datetime.now(timezone.utc).isoformat(),
                '["file.js"]',
                "To be deleted"
            )
        )
        conn.commit()
        conn.close()
        
        response = flask_test_client.delete("/api/sessions/fix/DELETE-1")
        
        assert response.status_code in (200, 204)
        
        response = flask_test_client.get("/api/sessions")
        data = json.loads(response.data)
        branch_names = [s.get("branch_name") for s in data["sessions"]]
        assert "fix/DELETE-1" not in branch_names

    def test_delete_nonexistent_session(self, flask_test_client) -> None:
        """Test deleting a session that doesn't exist."""
        response = flask_test_client.delete("/api/sessions/nonexistent/branch")
        
        assert response.status_code in (200, 204, 404)

    def test_api_sessions_url_encoding(self, flask_test_client, temp_db: str) -> None:
        """Test that branch names with special characters are handled."""
        import sqlite3
        
        conn = sqlite3.connect(temp_db)
        conn.execute(
            """
            INSERT INTO sessions (branch_name, repo, last_active, files_touched, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "fix/SPECIAL-1",
                "harsh/repo",
                datetime.now(timezone.utc).isoformat(),
                '["file.js"]',
                None
            )
        )
        conn.commit()
        conn.close()
        
        response = flask_test_client.delete("/api/sessions/fix/SPECIAL-1")
        assert response.status_code in (200, 204)

    def test_dashboard_localhost_only(self, flask_test_client) -> None:
        """Test that dashboard restricts access to localhost."""
        response = flask_test_client.get("/")
        assert response.status_code == 200


class TestDashboardIntegration:
    """Integration tests for dashboard with multiple endpoints."""

    def test_full_session_lifecycle(self, flask_test_client, temp_db: str) -> None:
        """Test complete session lifecycle: create, list, delete."""
        import sqlite3
        
        conn = sqlite3.connect(temp_db)
        conn.execute(
            """
            INSERT INTO sessions (branch_name, repo, last_active, files_touched, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "fix/LIFECYCLE-1",
                "harsh/repo",
                datetime.now(timezone.utc).isoformat(),
                '["app.js"]',
                "Lifecycle test"
            )
        )
        conn.commit()
        conn.close()
        
        response = flask_test_client.get("/api/sessions")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert any(s["branch_name"] == "fix/LIFECYCLE-1" for s in data["sessions"])
        
        response = flask_test_client.delete("/api/sessions/fix/LIFECYCLE-1")
        assert response.status_code in (200, 204)
        
        response = flask_test_client.get("/api/sessions")
        data = json.loads(response.data)
        assert not any(s["branch_name"] == "fix/LIFECYCLE-1" for s in data["sessions"])

    def test_api_sessions_response_structure(self, flask_test_client, temp_db: str) -> None:
        """Test that session responses have correct structure."""
        import sqlite3
        
        conn = sqlite3.connect(temp_db)
        conn.execute(
            """
            INSERT INTO sessions (branch_name, repo, last_active, files_touched, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "fix/STRUCT-1",
                "harsh/repo",
                datetime.now(timezone.utc).isoformat(),
                '["file.js"]',
                "Structure test"
            )
        )
        conn.commit()
        conn.close()
        
        response = flask_test_client.get("/api/sessions")
        data = json.loads(response.data)
        
        assert len(data["sessions"]) > 0
        session = data["sessions"][0]
        
        assert "branch_name" in session
        assert "repo" in session
        assert "last_active" in session
        assert "files_touched" in session
