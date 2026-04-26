from __future__ import annotations

import json
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Keep local modules importable when cb is launched via an installed entrypoint.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from integrations.github import display_github_summary, get_ci_status, get_pr_for_branch
from integrations.linear import (
    display_linear_summary,
    extract_ticket_id,
    get_ticket_details,
)
from integrations.slack import display_slack_summary, get_recent_messages
from storage.db import get_cache, get_last_session, save_cache, save_session


APP_DIR = Path.home() / ".context-bridge"
APP_CONFIG_PATH = APP_DIR / "config.json"
APP_ENV_PATH = APP_DIR / ".env"
console = Console()


def _is_valid_repo(repo: str) -> bool:
    """Validate owner/reponame format."""
    if "/" not in repo:
        return False
    owner, name = repo.split("/", 1)
    return bool(owner.strip() and name.strip())


def _load_app_config() -> dict[str, Any]:
    """Load persisted CLI config from ~/.context-bridge/config.json."""
    if not APP_CONFIG_PATH.exists():
        return {}

    try:
        return json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_app_config(data: dict[str, Any]) -> None:
    """Persist CLI config to ~/.context-bridge/config.json."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    APP_CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _get_repo_from_config_or_prompt() -> str:
    """Return saved repo or prompt the user once and persist it."""
    cfg = _load_app_config()
    saved_repo = str(cfg.get("default_repo", "")).strip()
    if saved_repo and _is_valid_repo(saved_repo):
        return saved_repo

    while True:
        repo = click.prompt("GitHub repo (owner/reponame)", type=str).strip()
        if _is_valid_repo(repo):
            cfg["default_repo"] = repo
            _save_app_config(cfg)
            return repo
        console.print("[yellow]Invalid repo format. Use owner/reponame.[/yellow]")


def _get_saved_repo() -> str | None:
    """Return saved default repo from app config, if valid."""
    cfg = _load_app_config()
    saved_repo = str(cfg.get("default_repo", "")).strip()
    return saved_repo if _is_valid_repo(saved_repo) else None


def _get_current_branch() -> str:
    """Read current git branch from the active repository."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise click.ClickException("Git is not installed or not available in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip() or "Not a git repository."
        raise click.ClickException(f"Could not detect current branch: {err}") from exc

    branch = result.stdout.strip()
    if not branch:
        raise click.ClickException("Could not detect current branch.")
    return branch


def _get_touched_files() -> list[str]:
    """Collect file paths from git status for session storage."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    files: list[str] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        if path_part and path_part not in seen:
            seen.add(path_part)
            files.append(path_part)
    return files


def _format_last_active(last_active_iso: str) -> str:
    """Convert ISO timestamp to readable relative time."""
    try:
        dt = datetime.fromisoformat(last_active_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt.astimezone(timezone.utc)
    except Exception:
        return "Unknown"

    total_seconds = max(0, int(delta.total_seconds()))
    hours = total_seconds // 3600
    if hours < 1:
        return "less than 1 hour ago"
    if hours == 1:
        return "1 hour ago"
    return f"{hours} hours ago"


def _upsert_env_file(path: Path, updates: dict[str, str]) -> None:
    """Update or append key-value pairs in .env without dropping other keys."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue

        key, _ = line.split("=", 1)
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def run_status_logic(interactive: bool = True, render: bool = True) -> dict[str, Any]:
    """Run the status workflow and optionally render terminal summaries.

    Args:
        interactive: Prompt for repo if missing when True.
        render: Print rich summaries to terminal when True.

    Returns:
        A JSON-safe dict describing fetched context.
    """
    if interactive:
        repo = _get_repo_from_config_or_prompt()
    else:
        repo = _get_saved_repo()
        if not repo:
            raise RuntimeError(
                "No default repo found. Run 'cb status' once in terminal or set "
                "~/.context-bridge/config.json with default_repo."
            )

    branch_name = _get_current_branch()
    files = _get_touched_files()

    github_summary: dict[str, Any] = {}
    linear_summary: dict[str, Any] = {}
    slack_summary: dict[str, Any] = {}
    github_error: str | None = None
    linear_error: str | None = None
    slack_error: str | None = None

    ticket_id = extract_ticket_id(branch_name)

    # Gather GitHub details for API output.
    try:
        pr_data = get_pr_for_branch(branch_name, repo)
        ci_data = get_ci_status(repo, branch_name)
        github_summary = {
            "pr": pr_data,
            "ci": ci_data,
        }
    except Exception as exc:
        github_error = str(exc)
        cached_github = get_cache(branch_name, "github", max_age_minutes=240)
        if isinstance(cached_github, dict) and cached_github:
            github_summary = cached_github
            github_error = f"{github_error} (showing cached GitHub context)"

    # Gather Linear details for API output.
    if ticket_id:
        try:
            linear_summary = get_ticket_details(ticket_id)
        except Exception as exc:
            linear_error = str(exc)
            cached_linear = get_cache(branch_name, "linear", max_age_minutes=240)
            if isinstance(cached_linear, dict) and cached_linear:
                linear_summary = cached_linear
                linear_error = f"{linear_error} (showing cached Linear context)"
    else:
        linear_summary = {
            "ticket_id": None,
            "title": "No ticket ID found in branch name",
            "status": "N/A",
            "assignee": "N/A",
            "priority": "N/A",
            "comments": [],
        }

    # Gather Slack details for API output.
    try:
        slack_summary = get_recent_messages(branch_name, ticket_id, max_messages=5)
    except Exception as exc:
        slack_error = str(exc)
        cached_slack = get_cache(branch_name, "slack", max_age_minutes=240)
        if isinstance(cached_slack, dict) and cached_slack:
            slack_summary = cached_slack
            slack_error = f"{slack_error} (showing cached Slack context)"
        else:
            slack_summary = {"query": "", "messages": []}

    save_session(branch_name, repo, files)

    if github_summary:
        save_cache(branch_name, "github", github_summary)
    if linear_summary:
        save_cache(branch_name, "linear", linear_summary)
    if slack_summary:
        save_cache(branch_name, "slack", slack_summary)

    fetched_at_iso = datetime.now(timezone.utc).isoformat()
    fetched_at_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if render:
        display_github_summary(repo)
        display_linear_summary(branch_name)
        display_slack_summary(branch_name, ticket_id)
        console.print(
            Panel(
                f"Context fetched at [bold]{fetched_at_human}[/bold]",
                border_style="green",
                title="Context Bridge",
                expand=False,
            )
        )

    return {
        "repo": repo,
        "branch_name": branch_name,
        "files_touched": files,
        "fetched_at": fetched_at_iso,
        "github": github_summary,
        "github_error": github_error,
        "linear": linear_summary,
        "linear_error": linear_error,
        "slack": slack_summary,
        "slack_error": slack_error,
    }


@click.group(help="Context Bridge developer productivity commands.")
def cli() -> None:
    """Main CLI group for cb commands."""


@cli.command(help="Fetch GitHub + Linear + Slack context for the current branch.")
def status() -> None:
    """Show cross-tool context and persist the current session."""
    console.print("[cyan]Fetching your context...[/cyan]")

    try:
        run_status_logic(interactive=True, render=True)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(help="Resume context from your last session on this branch.")
def resume() -> None:
    """Show last session details and suggest the next action."""
    console.print("[green]Resuming your last session...[/green]")

    branch_name = _get_current_branch()
    session = get_last_session(branch_name)
    if not session:
        console.print(
            "[yellow]No saved session found for this branch. Run 'cb status' first.[/yellow]"
        )
        return

    last_active = _format_last_active(str(session.get("last_active", "")))
    files = session.get("files_touched") or []
    files_text = ", ".join(files) if files else "No files recorded"
    repo = str(session.get("repo", "")).strip()

    comments_count = 0
    ci_status = "unknown"
    changes_text = "Could not fetch GitHub updates."

    if repo and _is_valid_repo(repo):
        try:
            pr_data = get_pr_for_branch(branch_name, repo)
            ci_data = get_ci_status(repo, branch_name)
            comments_count = len(pr_data.get("comments", []))
            ci_status = str(ci_data.get("status", "unknown"))
            ci_conclusion = ci_data.get("conclusion")
            pr_title = pr_data.get("title") or "No open PR for this branch"
            changes_text = (
                f"PR: {pr_title}\\n"
                f"Pending comments: {comments_count}\\n"
                f"CI: {ci_status} ({ci_conclusion})"
            )
        except Exception as exc:
            changes_text = f"Could not fetch GitHub updates: {exc}"

    if ci_status == "failure":
        next_step = "Fix CI"
    elif comments_count > 0:
        next_step = "Reply to comments"
    else:
        next_step = "Keep coding!"

    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("Last active", last_active)
    table.add_row("Files you touched", files_text)
    table.add_row("What changed since then", changes_text)
    table.add_row("Suggested next step", f"[bold]{next_step}[/bold]")

    console.print(
        Panel(
            table,
            title="[bold blue]Resume Summary[/bold blue]",
            border_style="bright_blue",
            expand=False,
        )
    )


@cli.command(help="Run first-time setup for tokens and default repo.")
def init() -> None:
    """Interactive setup wizard for token env and default repo config."""
    console.print("[cyan]Starting context-bridge setup wizard...[/cyan]")
    console.print("[dim]Tokens are saved to ~/.context-bridge/.env[/dim]")

    github_token = click.prompt("GitHub token", hide_input=True).strip()
    linear_token = click.prompt("Linear token", hide_input=True).strip()
    slack_token = click.prompt("Slack token", hide_input=True).strip()

    while True:
        default_repo = click.prompt("Default GitHub repo (owner/reponame)", type=str).strip()
        if _is_valid_repo(default_repo):
            break
        console.print("[yellow]Invalid repo format. Use owner/reponame.[/yellow]")

    env_path = APP_ENV_PATH
    updates = {
        "GITHUB_TOKEN": github_token,
        "LINEAR_TOKEN": linear_token,
        "SLACK_TOKEN": slack_token,
        "DEFAULT_REPO": default_repo,
    }

    _upsert_env_file(
        env_path,
        updates,
    )

    project_env_path = Path.cwd() / ".env"
    if project_env_path.exists() and project_env_path != env_path:
        _upsert_env_file(project_env_path, updates)

    cfg = _load_app_config()
    cfg["default_repo"] = default_repo
    _save_app_config(cfg)

    console.print(
        Panel(
            "[green]Setup complete![/green]\\n"
            f"Tokens saved to [bold]{env_path}[/bold]\\n"
            "Next steps:\\n"
            "1. Run [bold]cb status[/bold] to fetch context\\n"
            "2. Run [bold]cb resume[/bold] to continue work",
            title="Context Bridge Init",
            border_style="green",
            expand=False,
        )
    )


@cli.command(help="Check cb installation and local configuration health.")
def doctor() -> None:
    """Print diagnostic details for installation, token files, and config."""
    cb_path = shutil.which("cb") or "Not found in PATH"
    project_env = Path.cwd() / ".env"

    from config import GITHUB_TOKEN, LINEAR_TOKEN, SLACK_TOKEN

    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("cb executable", cb_path)
    table.add_row("python executable", sys.executable)
    table.add_row("user env", f"{APP_ENV_PATH} ({'exists' if APP_ENV_PATH.exists() else 'missing'})")
    table.add_row(
        "project env",
        f"{project_env} ({'exists' if project_env.exists() else 'missing'})",
    )
    table.add_row("default repo", _get_saved_repo() or "missing")
    table.add_row("GITHUB_TOKEN", "configured" if GITHUB_TOKEN else "missing")
    table.add_row("LINEAR_TOKEN", "configured" if LINEAR_TOKEN else "missing")
    table.add_row("SLACK_TOKEN", "configured" if SLACK_TOKEN else "missing")

    console.print(
        Panel(
            table,
            title="[bold blue]Context Bridge Doctor[/bold blue]",
            border_style="bright_blue",
            expand=False,
        )
    )


@cli.command(help="Start local context-bridge web dashboard.")
def web() -> None:
    """Start Flask dashboard on localhost and open it in a browser."""
    from dashboard.app import run_dashboard

    url = "http://localhost:4242"
    console.print(f"Dashboard running at {url}")
    webbrowser.open(url, new=2)
    run_dashboard()


if __name__ == "__main__":
    cli()