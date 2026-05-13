"""Tests for integrations/linear.py module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from integrations.linear import (
    extract_ticket_id,
    get_ticket_details,
)


class TestExtractTicketId:
    """Tests for extract_ticket_id() function."""

    def test_extract_ticket_id_standard(self) -> None:
        """Test extracting ticket ID from standard branch format."""
        result = extract_ticket_id("fix/AUTH-412-login")
        assert result == "AUTH-412"

    def test_extract_ticket_id_lowercase(self) -> None:
        """Test extracting ticket ID from lowercase branch name."""
        result = extract_ticket_id("con-5-login-timeout")
        assert result == "CON-5"

    def test_extract_ticket_id_with_username(self) -> None:
        """Test extracting ticket ID from branch with username prefix."""
        result = extract_ticket_id("pharshpathak703/con-5-login-timeout")
        assert result == "CON-5"

    def test_extract_ticket_id_no_match(self) -> None:
        """Test that branches without ticket IDs return None."""
        assert extract_ticket_id("main") is None
        assert extract_ticket_id("feature-dark-mode") is None
        assert extract_ticket_id("release/v1.0") is None

    def test_extract_ticket_id_various_formats(self) -> None:
        """Test extracting ticket IDs from various branch formats."""
        test_cases = [
            ("fix/FEAT-23-dark-mode", "FEAT-23"),
            ("bugfix/BUG-100-crash", "BUG-100"),
            ("DEV-5-something", "DEV-5"),
            ("PROJ-999-test", "PROJ-999"),
        ]
        
        for branch, expected_id in test_cases:
            result = extract_ticket_id(branch)
            assert result == expected_id

    def test_extract_ticket_id_multiple_ids_uses_first(self) -> None:
        """Test that when multiple IDs exist, the first one is returned."""
        result = extract_ticket_id("AUTH-412-con-5")
        assert result == "AUTH-412"


class TestGetTicketDetailsMocked:
    """Tests for get_ticket_details() with mocked API calls."""

    @patch("integrations.linear._require_token")
    @patch("integrations.linear.requests.post")
    def test_get_ticket_details_success(
        self, mock_post: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test successfully fetching ticket details from Linear API."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": {
                "issue": {
                    "id": "issue_123",
                    "identifier": "CON-5",
                    "title": "Fix login timeout",
                    "state": {"name": "In Progress"},
                    "assignee": {"name": "harsh"},
                    "priority": 1,
                    "description": "Users report 30s timeout on login",
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = get_ticket_details("CON-5")
        
        assert isinstance(result, dict)
        assert result.get("title") == "Fix login timeout"

    @patch("integrations.linear._require_token")
    @patch("integrations.linear.requests.post")
    def test_get_ticket_details_api_failure(
        self, mock_post: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test graceful handling when Linear API fails."""
        mock_token.return_value = "fake_token"
        mock_post.side_effect = requests.exceptions.RequestException("Connection timeout")
        
        with pytest.raises(RuntimeError):
            get_ticket_details("CON-5")

    @patch("integrations.linear._require_token")
    @patch("integrations.linear.requests.post")
    def test_get_ticket_details_auth_failure(
        self, mock_post: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test handling when Linear API returns 401 Unauthorized."""
        mock_token.return_value = "invalid_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        with pytest.raises(RuntimeError):
            get_ticket_details("CON-5")

    @patch("integrations.linear._require_token")
    @patch("integrations.linear.requests.post")
    def test_get_ticket_details_not_found(
        self, mock_post: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test handling when Linear ticket is not found."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": {"issue": None},
            "errors": [{"message": "Issue not found"}]
        }
        mock_post.return_value = mock_response
        
        try:
            result = get_ticket_details("NONEXISTENT-999")
            assert isinstance(result, dict)
        except RuntimeError:
            pass

    @patch("integrations.linear._require_token")
    def test_get_ticket_details_missing_token(self, mock_token: MagicMock) -> None:
        """Test handling when Linear token is not configured."""
        mock_token.side_effect = RuntimeError("Missing LINEAR_TOKEN")
        
        with pytest.raises(RuntimeError):
            get_ticket_details("CON-5")
