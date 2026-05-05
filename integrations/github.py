"""GitHub integration utilities for context-bridge.

This module fetches branch, PR, review comment, and CI details from GitHub,
then displays a compact summary in the terminal.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# We use lazy config getters so missing unrelated tokens do not break imports.
try:
    from config import get_github_token
except Exception as exc:  # pragma: no cover - depends on local env config
    get_github_token = None
    _CONFIG_IMPORT_ERROR = exc
else:
    _CONFIG_IMPORT_ERROR = None


GITHUB_API_BASE = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 20
console = Console()


def _require_token() -> str:
    """Return a usable GitHub token or raise a helpful error."""
    token_error: Exception | None = None

    if get_github_token is not None:
        try:
            return get_github_token()
        except Exception as exc:
            token_error = exc

    # Fallback: load directly from .env so GitHub integration can still work
    # even if config.py fails because of unrelated missing tokens.
    load_dotenv()
    env_token = os.getenv("GITHUB_TOKEN")
    if env_token:
        return env_token

    if token_error is not None:
        raise RuntimeError(str(token_error)) from token_error

    if _CONFIG_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Could not read GITHUB_TOKEN from config.py. "
            "Run 'cb init' to configure tokens."
        ) from _CONFIG_IMPORT_ERROR

    raise RuntimeError(
        "Missing GITHUB_TOKEN. Run 'cb init' to configure tokens."
    )


def _validate_repo(repo: str) -> tuple[str, str]:
    """Validate repo string format and return (owner, repo_name)."""
    if "/" not in repo:
        raise ValueError(
            "Invalid repo format. Use 'owner/reponame', for example 'john/my-app'."
        )

    owner, repo_name = repo.split("/", 1)
    if not owner or not repo_name:
        raise ValueError(
            "Invalid repo format. Use 'owner/reponame', for example 'john/my-app'."
        )

    return owner, repo_name


def _github_get(path_or_url: str, params: dict[str, Any] | None = None) -> Any:
    """Perform a GitHub API GET request with standard headers and error handling."""
    token = _require_token()
    is_full_url = path_or_url.startswith("http://") or path_or_url.startswith("https://")
    url = path_or_url if is_full_url else f"{GITHUB_API_BASE}{path_or_url}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "context-bridge",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise RuntimeError(f"GitHub API request failed for {url}: {exc}") from exc

    if response.status_code == 401:
        raise RuntimeError("GitHub auth failed (401). Check your GITHUB_TOKEN.")

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RuntimeError(
            f"GitHub API rate limit reached (429). Retry after ~{retry_after}s."
        )

    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        reset_epoch = response.headers.get("X-RateLimit-Reset")
        if reset_epoch:
            raise RuntimeError(
                "GitHub API rate limit exceeded. "
                f"Rate limit resets at epoch {reset_epoch}."
            )
        raise RuntimeError("GitHub API rate limit exceeded. Please retry later.")

    if not response.ok:
        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text
        raise RuntimeError(
            f"GitHub API error {response.status_code} for {url}: {message}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"GitHub API returned non-JSON response for {url}.") from exc


def get_current_branch() -> str:
    """Run git command and return the current branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git is not installed or not available in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        error_output = (exc.stderr or "").strip() or "unknown git error"
        raise RuntimeError(f"Failed to get current branch: {error_output}") from exc

    branch_name = result.stdout.strip()
    if not branch_name:
        raise RuntimeError("No active git branch found. Are you inside a git repository?")

    return branch_name


def get_pr_comments(repo: str, pr_number: int) -> list[dict[str, str]]:
    """Fetch PR review comments and return simplified comment details."""
    _validate_repo(repo)
    comments_payload = _github_get(f"/repos/{repo}/pulls/{pr_number}/comments")

    comments: list[dict[str, str]] = []
    for comment in comments_payload:
        user = comment.get("user") or {}
        comments.append(
            {
                "author": user.get("login", "unknown"),
                "body": comment.get("body", ""),
                "created_at": comment.get("created_at", ""),
            }
        )

    return comments


def get_pr_for_branch(branch_name: str, repo: str) -> dict[str, Any]:
    """Find the open PR for a branch and include its review comments."""
    owner, _ = _validate_repo(repo)
    if not branch_name:
        raise ValueError("branch_name cannot be empty.")

    pulls_payload = _github_get(
        f"/repos/{repo}/pulls",
        params={"head": f"{owner}:{branch_name}", "state": "open"},
    )

    if not pulls_payload:
        return {
            "number": None,
            "title": "No open PR for this branch",
            "url": "",
            "comments": [],
        }

    pr = pulls_payload[0]
    pr_number = pr.get("number")
    comments = get_pr_comments(repo, pr_number) if pr_number else []

    return {
        "number": pr_number,
        "title": pr.get("title", "Untitled PR"),
        "url": pr.get("html_url", ""),
        "comments": comments,
    }


def get_ci_status(repo: str, branch_name: str) -> dict[str, str | None]:
    """Get latest GitHub Actions run status and failed job details."""
    _validate_repo(repo)
    if not branch_name:
        raise ValueError("branch_name cannot be empty.")

    runs_payload = _github_get(
        f"/repos/{repo}/actions/runs",
        params={"branch": branch_name, "per_page": 1},
    )
    workflow_runs = runs_payload.get("workflow_runs", [])

    if not workflow_runs:
        return {"status": "no_runs", "conclusion": None, "failed_job": None}

    latest_run = workflow_runs[0]
    conclusion = latest_run.get("conclusion")
    raw_status = latest_run.get("status", "unknown")

    if conclusion == "success":
        normalized_status = "success"
    elif conclusion in {"failure", "cancelled", "timed_out", "stale", "action_required"}:
        normalized_status = "failure"
    else:
        normalized_status = raw_status

    failed_job: str | None = None
    if normalized_status == "failure":
        jobs_url = latest_run.get("jobs_url")
        if jobs_url:
            jobs_payload = _github_get(jobs_url)
            for job in jobs_payload.get("jobs", []):
                job_conclusion = job.get("conclusion")
                if job_conclusion in {"failure", "cancelled", "timed_out", "action_required"}:
                    failed_job = job.get("name", "Unknown job")
                    break

    return {
        "status": normalized_status,
        "conclusion": conclusion or raw_status,
        "failed_job": failed_job,
    }


def display_github_summary(repo: str, branch_name: str | None = None, data: dict[str, Any] | None = None) -> None:
    """Fetch branch/PR/CI details and print a rich terminal summary panel."""
    try:
        if not branch_name:
            branch_name = get_current_branch()
        if data is not None:
            pr_data = data.get("pr", {})
            ci_data = data.get("ci", {})
        else:
            pr_data = get_pr_for_branch(branch_name, repo)
            ci_data = get_ci_status(repo, branch_name)
    except Exception as exc:
        console.print(f"[bold red]GitHub summary failed:[/bold red] {exc}")
        return

    unresolved_count = len(pr_data.get("comments", []))
    pr_number = pr_data.get("number")
    pr_title = pr_data.get("title", "No PR title")
    pr_url = pr_data.get("url", "")

    if pr_number:
        pr_line = (
            f"[bold]{pr_title}[/bold]\n"
            f"#{pr_number}\n"
            f"{pr_url}\n"
            f"Unresolved comments: [bold]{unresolved_count}[/bold]"
        )
    else:
        pr_line = "No open PR for the current branch"

    ci_status = ci_data.get("status")
    ci_conclusion = ci_data.get("conclusion")
    failed_job = ci_data.get("failed_job")

    if ci_status == "success":
        ci_line = "[green]✅ CI Passed[/green]"
    elif ci_status == "failure":
        if failed_job:
            ci_line = f"[red]❌ CI Failed[/red] ({failed_job}, {ci_conclusion})"
        else:
            ci_line = f"[red]❌ CI Failed[/red] ({ci_conclusion})"
    elif ci_status == "no_runs":
        ci_line = "[yellow]No workflow runs found for this branch[/yellow]"
    else:
        ci_line = f"[yellow]CI status: {ci_status} ({ci_conclusion})[/yellow]"

    summary_table = Table.grid(padding=(0, 1))
    summary_table.add_column(style="bold cyan", no_wrap=True)
    summary_table.add_column()
    summary_table.add_row("Branch", f"[bold]{branch_name}[/bold]")
    summary_table.add_row("Pull Request", pr_line)
    summary_table.add_row("CI", ci_line)

    panel = Panel(
        summary_table,
        title="[bold blue]GitHub Context Summary[/bold blue]",
        border_style="bright_blue",
        expand=False,
    )
    console.print(panel)