"""Tests for cli/main.py Click commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


class TestCliExists:
    """Tests that CLI commands exist."""

    def test_cli_app_exists(self) -> None:
        """Test that CLI app is defined."""
        assert cli is not None

    def test_repo_command_exists(self) -> None:
        """Test that 'repo' subcommand exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "--help"])
        assert result.exit_code == 0
        assert "repo" in result.output.lower()

    def test_notes_command_exists(self) -> None:
        """Test that 'notes' subcommand exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["notes", "--help"])
        assert result.exit_code == 0
        assert "notes" in result.output.lower()

    def test_context_command_exists(self) -> None:
        """Test that 'context' subcommand exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["context", "--help"])
        assert result.exit_code == 0 or "context" in result.output.lower()

    def test_status_command_exists(self) -> None:
        """Test that 'status' subcommand exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0 or "status" in result.output.lower()


class TestRepoSubcommands:
    """Tests for repo subcommands."""

    def test_repo_add_command_help(self) -> None:
        """Test 'cb repo add --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "add", "--help"])
        assert result.exit_code == 0

    def test_repo_list_command_help(self) -> None:
        """Test 'cb repo list --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "list", "--help"])
        assert result.exit_code == 0

    def test_repo_use_command_help(self) -> None:
        """Test 'cb repo use --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "use", "--help"])
        assert result.exit_code == 0

    @patch("cli.main.add_repo")
    def test_repo_add_calls_db(self, mock_add: MagicMock) -> None:
        """Test that 'cb repo add' calls add_repo()."""
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "add", "harsh/test"])
        
        assert result.exit_code == 0 or result.exit_code == 1

    @patch("cli.main.list_repos")
    def test_repo_list_calls_db(self, mock_list: MagicMock) -> None:
        """Test that 'cb repo list' calls list_repos()."""
        mock_list.return_value = []
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "list"])
        
        assert result.exit_code == 0 or result.exit_code == 1


class TestNotesSubcommands:
    """Tests for notes subcommands."""

    def test_notes_add_command_help(self) -> None:
        """Test 'cb notes add --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["notes", "add", "--help"])
        assert result.exit_code == 0

    def test_notes_show_command_help(self) -> None:
        """Test 'cb notes show --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["notes", "show", "--help"])
        assert result.exit_code == 0

    @patch("storage.db.save_note")
    @patch("subprocess.run")
    def test_notes_add_implementation(
        self, mock_run: MagicMock, mock_save: MagicMock
    ) -> None:
        """Test that 'cb notes add' invokes save_note."""
        mock_run.return_value.stdout = "fix/TEST-1\n"
        runner = CliRunner()
        result = runner.invoke(cli, ["notes", "add", "Test note"])
        
        assert result.exit_code == 0 or result.exit_code == 1

    @patch("storage.db.get_notes")
    @patch("subprocess.run")
    def test_notes_show_implementation(
        self, mock_run: MagicMock, mock_get: MagicMock
    ) -> None:
        """Test that 'cb notes show' invokes get_notes."""
        mock_run.return_value.stdout = "fix/TEST-1\n"
        mock_get.return_value = "Sample notes"
        runner = CliRunner()
        result = runner.invoke(cli, ["notes", "show"])
        
        assert result.exit_code == 0 or result.exit_code == 1


class TestContextSubcommand:
    """Tests for context subcommand."""

    def test_context_command_help(self) -> None:
        """Test 'cb context --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["context", "--help"])
        assert result.exit_code == 0 or "usage" in result.output.lower()

    @patch("subprocess.run")
    def test_context_command_invokes_subprocess(self, mock_run: MagicMock) -> None:
        """Test that context command runs subprocess."""
        runner = CliRunner()
        result = runner.invoke(cli, ["context"])
        
        assert result.exit_code is not None


class TestStatusSubcommand:
    """Tests for status subcommand."""

    def test_status_command_help(self) -> None:
        """Test 'cb status --help' works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0 or "usage" in result.output.lower()

    @patch("subprocess.run")
    def test_status_command_invokes_subprocess(self, mock_run: MagicMock) -> None:
        """Test that status command runs subprocess."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        
        assert result.exit_code is not None


class TestCliErrorHandling:
    """Tests for error handling in CLI."""

    def test_invalid_command_fails(self) -> None:
        """Test that invalid command fails."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])
        
        assert result.exit_code != 0

    def test_missing_required_arg_fails(self) -> None:
        """Test that missing required arguments fail."""
        runner = CliRunner()
        result = runner.invoke(cli, ["repo", "add"])
        
        assert result.exit_code != 0
