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
from storage.db import (
    add_repo,
    get_active_repo,
    get_cache,
    get_last_session,
    list_repos,
    remove_repo,
    repo_exists,
    save_cache,
    save_session,
    set_active_repo,
)


APP_DIR = Path.home() / ".context-bridge"
APP_CONFIG_PATH = APP_DIR / "config.json"
APP_ENV_PATH = APP_DIR / ".env"
console = Console()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _is_valid_repo(repo: str) -> bool:
    """Validate owner/reponame format (must contain exactly one '/')."""
    if "/" not in repo:
        return False
    parts = repo.split("/")
    if len(parts) != 2:
        return False
    owner, name = parts
    return bool(owner.strip() and name.strip())


def _require_active_repo() -> str:
    """Return the active repo from the database.

    Raises click.ClickException with a helpful message when no repo is set.
    """
    repo = get_active_repo()
    if repo:
        return repo
    raise click.ClickException(
        "No active repo set. Run: cb repo add owner/repo"
    )


# ---------------------------------------------------------------------------
# App config helpers (kept for backward compat — tokens reference only)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# .env file helper (used only in cb init for tokens)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Core status logic (used by cb status and dashboard API)
# ---------------------------------------------------------------------------

def run_status_logic(interactive: bool = True, render: bool = True) -> dict[str, Any]:
    """Run the status workflow and optionally render terminal summaries.

    Args:
        interactive: Prompt for repo if missing when True.
        render: Print rich summaries to terminal when True.

    Returns:
        A JSON-safe dict describing fetched context.
    """
    # Always read repo from SQLite — no more config.json or .env fallback.
    repo = get_active_repo()
    if not repo:
        if interactive:
            raise click.ClickException(
                "No active repo set. Run: cb repo add owner/repo"
            )
        raise RuntimeError(
            "No active repo set. Run 'cb repo add owner/repo' to configure one."
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

    from config import GITHUB_TOKEN, LINEAR_TOKEN, SLACK_TOKEN

    if not GITHUB_TOKEN:
        if interactive:
            raise click.ClickException("GitHub token required. Run cb init")
        raise RuntimeError("GitHub token required. Run cb init")

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
    if not LINEAR_TOKEN:
        linear_summary = {
            "ticket_id": None,
            "title": "Linear skipped (no token)",
            "status": "N/A",
            "assignee": "N/A",
            "priority": "N/A",
            "comments": [],
        }
    elif ticket_id:
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
    if not SLACK_TOKEN:
        slack_summary = {"query": "", "messages": [], "status": "skipped"}
    else:
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
        if LINEAR_TOKEN:
            display_linear_summary(branch_name)
        if SLACK_TOKEN:
            display_slack_summary(branch_name, ticket_id)
        console.print(
            Panel(
                f"Context fetched at [bold]{fetched_at_human}[/bold]",
                border_style="green",
                title="Context Bridge",
                expand=False,
            )
        )
        if not LINEAR_TOKEN:
            console.print("[dim]Linear skipped (no token) · Run cb init to add[/dim]")
        if not SLACK_TOKEN:
            console.print("[dim]Slack skipped (no token) · Run cb init to add[/dim]")

        from storage.db import get_notes
        branch_notes = get_notes(branch_name)
        if branch_notes:
            preview = branch_notes.replace('\n', ' ')
            if len(preview) > 100:
                preview = preview[:97] + "..."
            console.print(f"📝 Your notes: [dim]{preview}[/dim]")

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


# ===================================================================
# CLI definition
# ===================================================================

@click.group(
    help="Context Bridge — your dev tools, unified.\n\n"
    "Pulls context from GitHub, Linear, and Slack so you never lose\n"
    "track of where you left off. Run 'cb status' to get started.",
)
def cli() -> None:
    """Main CLI group for cb commands."""


# ---------------------------------------------------------------------------
# cb status
# ---------------------------------------------------------------------------

@cli.command(
    help="Fetch GitHub + Linear + Slack context for the current branch.\n\n"
    "Shows PR status, CI results, Linear ticket details, and recent\n"
    "Slack messages — all in one view. Uses the active repo set via\n"
    "'cb repo'.",
)
def status() -> None:
    """Show cross-tool context and persist the current session."""
    console.print("[cyan]Fetching your context...[/cyan]")

    try:
        run_status_logic(interactive=True, render=True)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# cb resume
# ---------------------------------------------------------------------------

@cli.command(
    help="Resume context from your last session on this branch.\n\n"
    "Shows when you were last active, which files you touched,\n"
    "what changed while you were away, and suggests a next step.",
)
def resume() -> None:
    """Show last session details and suggest the next action."""
    # Ensure an active repo is set before attempting anything.
    repo = get_active_repo()
    if not repo:
        console.print(
            "[red]No active repo set.[/red] Run: [bold]cb repo add owner/repo[/bold]"
        )
        return

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


# ---------------------------------------------------------------------------
# cb export
# ---------------------------------------------------------------------------

@cli.command(
    help="Export all context for the current branch to a markdown file.\n\n"
    "Gathers PR info, CI status, Linear ticket details, and recent\n"
    "Slack messages, and saves them into a clean document you can share."
)
def export() -> None:
    """Generate a clean markdown document with all branch context."""
    # 1. Gather all context for current branch (same as cb status) by calling all integrations
    console.print("[cyan]Gathering context for export...[/cyan]")
    try:
        context = run_status_logic(interactive=True, render=False)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    branch = context.get("branch_name", "unknown-branch")

    # 2. Generate a clean markdown document with the specified structure
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

    md_lines = []
    md_lines.append("---")
    md_lines.append(f"# Context Export — {branch}")
    md_lines.append(f"Generated: {datetime_str}")
    md_lines.append("")

    # Branch section
    md_lines.append("## Branch")
    md_lines.append(branch)
    md_lines.append("")

    # Linear Ticket section
    md_lines.append("## Linear Ticket")
    linear = context.get("linear", {})
    ticket_id = linear.get("ticket_id")
    if ticket_id:
        md_lines.append(f"- ID: {ticket_id}")
        md_lines.append(f"- Title: {linear.get('title', 'N/A')}")
        md_lines.append(f"- Status: {linear.get('status', 'N/A')}")
        md_lines.append(f"- Assignee: {linear.get('assignee', 'N/A')}")
        md_lines.append(f"- Priority: {linear.get('priority', 'N/A')}")
    else:
        md_lines.append("No ticket found.")
    md_lines.append("")

    # GitHub PR section
    md_lines.append("## GitHub PR")
    github = context.get("github", {})
    pr_data = github.get("pr", {})
    pr_number = pr_data.get("number")
    if pr_number:
        md_lines.append(f"- PR #{pr_number}: {pr_data.get('title', 'N/A')}")
        md_lines.append(f"- URL: {pr_data.get('url', 'N/A')}")
        unresolved = pr_data.get("unresolved_comments", len(pr_data.get("comments", [])))
        md_lines.append(f"- Unresolved Comments: {unresolved}")
        reviewers = pr_data.get("reviewers", [])
        if reviewers:
            rev_str = ", ".join([r.get("login", "unknown") for r in reviewers])
        else:
            rev_str = "None"
        md_lines.append(f"- Reviewer: {rev_str}")
    else:
        md_lines.append("No open PR for this branch.")
    md_lines.append("")

    # CI Status section
    md_lines.append("## CI Status")
    ci_data = github.get("ci", {})
    if ci_data and ci_data.get("status") != "no_runs":
        status_raw = ci_data.get("status", "unknown").capitalize()
        md_lines.append(f"- Status: {status_raw}")
        md_lines.append(f"- Last Run: {now.strftime('%Y-%m-%d %H:%M')}")
    else:
        md_lines.append("No CI data.")
    md_lines.append("")

    # Slack Messages section
    md_lines.append("## Slack Messages")
    slack = context.get("slack", {})
    messages = slack.get("messages", [])
    if messages:
        for msg in messages:
            author = msg.get("author", "unknown")
            channel = msg.get("channel", "unknown")
            text = msg.get("text", "")
            md_lines.append(f"- {author} in #{channel}: \"{text}\"")
    else:
        md_lines.append("No recent messages.")
    md_lines.append("")

    # My Notes section
    md_lines.append("## My Notes")
    from storage.db import get_notes
    notes = get_notes(branch)
    if notes:
        for line in notes.splitlines():
            line = line.strip()
            if line:
                if line.startswith("- "):
                    md_lines.append(line)
                else:
                    md_lines.append(f"- {line}")
    else:
        md_lines.append("- No notes.")
    md_lines.append("")

    # Last Session section
    md_lines.append("## Last Session")
    from storage.db import get_last_session
    session = get_last_session(branch)
    if session:
        last_active = _format_last_active(str(session.get("last_active", "")))
        files = session.get("files_touched") or []
        files_str = ", ".join(files) if files else "None"
        md_lines.append(f"- Last Active: {last_active}")
        md_lines.append(f"- Files Touched: {files_str}")
    else:
        md_lines.append("- No previous session recorded.")
    md_lines.append("---")

    md_content = "\n".join(md_lines)

    # 3. Save this file as: context-bridge-export-{branch-name}-{date}.md in the CWD
    safe_branch = branch.replace("/", "-")
    filename = f"context-bridge-export-{safe_branch}-{date_str}.md"
    filepath = Path.cwd() / filename
    filepath.write_text(md_content, encoding="utf-8")

    # 4. Also print the content to terminal using Rich
    console.print(Panel(md_content, title=filename, border_style="green", expand=False))

    # 5. Show at end message
    console.print(f"[green]✓ Exported to {filename}[/green]")
    console.print("→ Paste this into your PR description, standup, or Slack")


# ---------------------------------------------------------------------------
# cb init
# ---------------------------------------------------------------------------

@cli.command(
    help="Run first-time setup for API tokens and default repo.\n\n"
    "Saves GitHub, Linear, and Slack tokens to ~/.context-bridge/.env.\n"
    "Optionally sets a default repo (you can also add repos later\n"
    "with 'cb repo add').",
)
def init() -> None:
    """Interactive setup wizard for token env and default repo config.

    Tokens are saved to ~/.context-bridge/.env.
    Repo is stored in SQLite via db.py (not .env or config.json).
    """
    from config import GITHUB_TOKEN, LINEAR_TOKEN, SLACK_TOKEN

    console.print("[cyan]Starting context-bridge setup wizard...[/cyan]")
    console.print("[dim]Tokens are saved to ~/.context-bridge/.env[/dim]")

    def prompt_token(name: str, existing: str | None, optional: bool = False) -> str | None:
        if existing:
            val = click.prompt(f"{name} already set. Press Enter to keep, or type new token", default="", show_default=False).strip()
            return existing if not val else val

        req_str = "(press Enter to skip)" if optional else "(required)"
        val = click.prompt(f"{name} {req_str}", hide_input=True, default="", show_default=False).strip()
        return None if not val else val

    github_token = prompt_token("GitHub Token", GITHUB_TOKEN, optional=False)
    while not github_token:
        github_token = click.prompt("GitHub Token (required)", hide_input=True, default="", show_default=False).strip()

    linear_token = prompt_token("Linear Token", LINEAR_TOKEN, optional=True)
    slack_token = prompt_token("Slack Token", SLACK_TOKEN, optional=True)

    # Repo entry is optional — user can press Enter to skip.
    default_repo = click.prompt(
        "Default GitHub repo (owner/reponame)",
        type=str,
        default="",
        show_default=False,
    ).strip()

    # Save tokens to .env (repo is NOT stored in .env anymore).
    env_updates = {}
    if github_token:
        env_updates["GITHUB_TOKEN"] = github_token
    if linear_token:
        env_updates["LINEAR_TOKEN"] = linear_token
    if slack_token:
        env_updates["SLACK_TOKEN"] = slack_token

    _upsert_env_file(APP_ENV_PATH, env_updates)

    # Also update project-level .env if one exists (tokens only).
    project_env_path = Path.cwd() / ".env"
    if project_env_path.exists() and project_env_path != APP_ENV_PATH:
        _upsert_env_file(project_env_path, env_updates)

    # Store repo in SQLite if the user provided one.
    if default_repo and _is_valid_repo(default_repo):
        add_repo(default_repo)
        repo_msg = f"Active repo set to [bold]{default_repo}[/bold]"
    else:
        repo_msg = "[dim]Tip: run [bold]cb repo add owner/repo[/bold] anytime to add a repo[/dim]"

    console.print(
        Panel(
            f"[green]Setup complete![/green]\\n"
            f"Tokens saved to [bold]{APP_ENV_PATH}[/bold]\\n"
            f"{repo_msg}\\n"
            "Next steps:\\n"
            "1. Run [bold]cb status[/bold] to fetch context\\n"
            "2. Run [bold]cb resume[/bold] to continue work",
            title="Context Bridge Init",
            border_style="green",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# cb doctor
# ---------------------------------------------------------------------------

@cli.command(
    help="Check cb installation and local configuration health.\n\n"
    "Shows token status, active repo, executable paths, and .env\n"
    "file locations. Useful for debugging setup issues.",
)
def doctor() -> None:
    """Print diagnostic details for installation, token files, and config."""
    cb_path = shutil.which("cb") or "Not found in PATH"
    project_env = Path.cwd() / ".env"

    from config import GITHUB_TOKEN, LINEAR_TOKEN, SLACK_TOKEN

    active_repo = get_active_repo() or "not set"

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
    table.add_row("active repo", active_repo)
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


# ---------------------------------------------------------------------------
# cb web
# ---------------------------------------------------------------------------

@cli.command(
    help="Start local context-bridge web dashboard.\n\n"
    "Opens a browser to http://localhost:4242 with a live view of\n"
    "all your branch sessions, PR status, and integration data.",
)
def web() -> None:
    """Start Flask dashboard on localhost and open it in a browser."""
    from dashboard.app import run_dashboard

    url = "http://localhost:4242"
    console.print(f"Dashboard running at {url}")
    webbrowser.open(url, new=2)
    run_dashboard()


# ---------------------------------------------------------------------------
# cb repo — command group for multi-repo management
# ---------------------------------------------------------------------------

@cli.group(
    help="Manage saved repos — add, switch, list, or remove.\n\n"
    "Tokens (GitHub, Linear, Slack) stay the same — only the active\n"
    "repo changes. You can save multiple repos and switch between\n"
    "them instantly with 'cb repo use'.\n\n"
    "Examples:\n\n"
    "  cb repo add  harsh/my-app      # Add and activate\n\n"
    "  cb repo use  harsh/other-app   # Switch active repo\n\n"
    "  cb repo list                   # Show all saved repos\n\n"
    "  cb repo current                # Show active repo",
)
def repo() -> None:
    """Parent group for repo subcommands (add, use, list, remove, current)."""


@repo.command(
    "add",
    help="Add a new repo and set it as active.\n\n"
    "FULL_NAME must be in owner/repo format (e.g. harsh/my-app).\n"
    "If the repo was already added, it is simply set as active.",
)
@click.argument("full_name")
def repo_add(full_name: str) -> None:
    """Add a repo to the saved list and activate it.

    FULL_NAME must be in owner/repo format (e.g. harsh/my-app).
    """
    full_name = full_name.strip()

    # Validate format — must contain exactly one '/'.
    if not _is_valid_repo(full_name):
        console.print(
            "[red]Invalid repo format.[/red] Use [bold]owner/reponame[/bold] "
            "(e.g. harsh/my-app)"
        )
        raise SystemExit(1)

    # Check if already saved.
    if repo_exists(full_name):
        set_active_repo(full_name)
        console.print(
            f"[green]✓[/green] '{full_name}' already saved — set as active repo"
        )
        return

    add_repo(full_name)
    console.print(
        f"[green]✓[/green] Added and set [bold]'{full_name}'[/bold] as active repo"
    )


@repo.command(
    "use",
    help="Switch the active repo to an already-saved one.\n\n"
    "The repo must have been previously added with 'cb repo add'.\n"
    "All subsequent 'cb status' and 'cb resume' calls will use it.",
)
@click.argument("full_name")
def repo_use(full_name: str) -> None:
    """Switch active repo. The repo must already be added.

    FULL_NAME must be in owner/repo format (e.g. harsh/my-app).
    """
    full_name = full_name.strip()

    if not repo_exists(full_name):
        console.print(
            f"[red]Repo '{full_name}' not found.[/red] "
            f"Add it first: [bold]cb repo add {full_name}[/bold]"
        )
        raise SystemExit(1)

    set_active_repo(full_name)
    console.print(f"[green]✓[/green] Switched to [bold]'{full_name}'[/bold]")


@repo.command(
    "list",
    help="Show all saved repos in a table.\n\n"
    "The currently active repo is highlighted in green.",
)
def repo_list() -> None:
    """Display a Rich table of all saved repos with active status."""
    repos = list_repos()

    if not repos:
        console.print(
            "[yellow]No repos saved yet.[/yellow] "
            "Run: [bold]cb repo add owner/repo[/bold]"
        )
        return

    table = Table(title="Saved Repos", border_style="bright_blue", expand=False)
    table.add_column("Name", style="bold")
    table.add_column("Full Name")
    table.add_column("Status", justify="center")

    for r in repos:
        if r["is_active"]:
            # Highlight the active repo in green.
            table.add_row(
                f"[green]{r['name']}[/green]",
                f"[green]{r['full_name']}[/green]",
                "[green]Active ✓[/green]",
            )
        else:
            table.add_row(r["name"], r["full_name"], "-")

    console.print(table)
    console.print(f"[dim]Total repos: {len(repos)}[/dim]")


@repo.command(
    "remove",
    help="Remove a saved repo after confirmation.\n\n"
    "If the removed repo was the active one, you will be\n"
    "prompted to set a new active repo.",
)
@click.argument("full_name")
def repo_remove(full_name: str) -> None:
    """Remove a repo from the saved list after user confirmation.

    FULL_NAME must be in owner/repo format (e.g. harsh/my-app).
    """
    full_name = full_name.strip()

    if not repo_exists(full_name):
        console.print(f"[red]Repo '{full_name}' not found.[/red]")
        raise SystemExit(1)

    # Check if this is the currently active repo so we can warn the user.
    was_active = get_active_repo() == full_name

    # Ask for confirmation before destructive action.
    if not click.confirm(f"Remove {full_name}?", default=False):
        console.print("[dim]Cancelled.[/dim]")
        return

    remove_repo(full_name)
    console.print(f"[green]✓[/green] Removed '{full_name}'")

    if was_active:
        console.print(
            "[yellow]⚠ That was your active repo.[/yellow] "
            "Run [bold]cb repo use owner/repo[/bold] to set a new one."
        )


@repo.command(
    "current",
    help="Show the currently active repo.\n\n"
    "If no repo is set, shows a hint to run 'cb repo add'.",
)
def repo_current() -> None:
    """Print the currently active repo name, or a hint if none is set."""
    active = get_active_repo()
    if active:
        console.print(f"Active repo: [bold green]{active}[/bold green]")
    else:
        console.print(
            "[yellow]No active repo set.[/yellow] "
            "Run: [bold]cb repo add owner/repo[/bold]"
        )


# ---------------------------------------------------------------------------
# Notes Management commands
# ---------------------------------------------------------------------------

@cli.group(
    help="Manage notes attached to the current branch session.\n\n"
         "Notes are specific to each branch, so you can leave yourself\n"
         "reminders or context before switching contexts."
)
def notes() -> None:
    """Parent group for note management on the active branch."""
    pass


@notes.command("add")
@click.argument("text")
def notes_add(text: str) -> None:
    """Add a note to current branch session."""
    from storage.db import save_note
    try:
        # Import conditionally (if inside function since we import dynamically everywhere else)
        from integrations.github import get_current_branch
    except ImportError:
        pass
        
    branch = get_current_branch()
    if not branch:
        console.print("[red]Not in a git repository or no branch found.[/red]")
        raise SystemExit(1)

    try:
        save_note(branch, text)
        console.print(f"[green]✓ Note saved to {branch}[/green]")
    except RuntimeError as exc:
        console.print(f"[red]Error saving note: {exc}[/red]")
        raise SystemExit(1)


@notes.command("show")
def notes_show() -> None:
    """Show all notes for current branch."""
    from storage.db import get_notes
    from integrations.github import get_current_branch

    branch = get_current_branch()
    if not branch:
        console.print("[red]Not in a git repository or no branch found.[/red]")
        raise SystemExit(1)

    branch_notes = get_notes(branch)
    if not branch_notes:
        console.print(f"[dim]No notes found for branch {branch}.[/dim]")
        return

    console.print(
        Panel(
            branch_notes,
            title=f"Notes — {branch}",
            border_style="yellow",
            expand=False,
        )
    )


@notes.command("clear")
def notes_clear() -> None:
    """Clear all notes for current branch."""
    from storage.db import clear_notes
    from integrations.github import get_current_branch

    branch = get_current_branch()
    if not branch:
        console.print("[red]Not in a git repository or no branch found.[/red]")
        raise SystemExit(1)

    if not click.confirm(f"Clear all notes for this branch? [y/N]", default=False):
        console.print("[dim]Cancelled.[/dim]")
        return

    clear_notes(branch)
    console.print("[green]✓ Notes cleared[/green]")


if __name__ == "__main__":
    cli()