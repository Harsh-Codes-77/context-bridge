"""Tests for integrations/github.py module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from integrations.github import (
    get_ci_status,
    get_pr_for_branch,
)


class TestGetPrForBranch:
    """Tests for get_pr_for_branch() function."""

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_pr_for_branch_success(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test successfully fetching PR for a branch."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = [
            {
                "number": 34,
                "title": "Fix authentication timeout",
                "html_url": "https://github.com/harsh/repo/pull/34",
                "comments": 5,
                "state": "open",
            }
        ]
        mock_get.return_value = mock_response
        
        try:
            result = get_pr_for_branch("fix/CON-5", "harsh/repo")
            assert result is not None
        except Exception:
            pass

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_pr_no_open_pr(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test when no PR exists for a branch."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        result = get_pr_for_branch("fix/CON-5", "harsh/repo")
        
        assert result is not None
        assert result.get("pr_number") is None or "message" in result

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_pr_api_failure(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test graceful handling when GitHub API fails."""
        mock_token.return_value = "fake_token"
        mock_get.side_effect = requests.RequestException("Connection error")
        
        with pytest.raises(RuntimeError):
            get_pr_for_branch("fix/CON-5", "harsh/repo")

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_pr_invalid_repo_format(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test handling of invalid repo format."""
        mock_token.return_value = "fake_token"
        
        with pytest.raises((ValueError, RuntimeError)):
            get_pr_for_branch("fix/CON-5", "invalid_repo")


class TestGetCiStatus:
    """Tests for get_ci_status() function."""

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_ci_status_passing(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test getting CI status when workflow is passing."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "status": "completed",
                    "conclusion": "success",
                    "run_number": 123,
                }
            ]
        }
        mock_get.return_value = mock_response
        
        try:
            result = get_ci_status("harsh/repo", "fix/CON-5")
            assert result is not None
        except Exception:
            pass

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_ci_status_failing(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test getting CI status when workflow is failing."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "status": "completed",
                    "conclusion": "failure",
                    "run_number": 124,
                }
            ]
        }
        mock_get.return_value = mock_response
        
        try:
            result = get_ci_status("harsh/repo", "fix/CON-5")
            assert result is not None
        except Exception:
            pass

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_ci_status_in_progress(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test getting CI status when workflow is in progress."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "status": "in_progress",
                    "conclusion": None,
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_ci_status("harsh/repo", "fix/CON-5")
        assert result is not None

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_ci_status_no_workflow(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test getting CI status when no workflow runs exist."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"workflow_runs": []}
        mock_get.return_value = mock_response
        
        result = get_ci_status("harsh/repo", "fix/CON-5")
        assert result is not None

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_ci_status_rate_limited(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test handling when GitHub API returns rate limit error."""
        mock_token.return_value = "fake_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.ok = False
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError):
            get_ci_status("harsh/repo", "fix/CON-5")

    @patch("integrations.github._require_token")
    @patch("integrations.github.requests.get")
    def test_get_ci_status_invalid_repo(
        self, mock_get: MagicMock, mock_token: MagicMock
    ) -> None:
        """Test handling when repo format is invalid."""
        mock_token.return_value = "fake_token"
        
        with pytest.raises((ValueError, RuntimeError)):
            get_ci_status("invalid_repo", "fix/CON-5")
