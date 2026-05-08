"""Standup report generation for context-bridge.

This module aggregates branch activity from the last 24 hours and generates
a formatted daily standup report pulling from GitHub PR comments, CI status,
and Linear ticket updates.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from rich.console import Console

from integrations.github import get_ci_status, get_pr_for_branch
from integrations.linear import extract_ticket_id, get_ticket_details
from storage.db import get_cache, get_sessions_last_24h


console = Console()


def _parse_iso_datetime(iso_str: str) -> datetime:
    """Parse ISO datetime string and return datetime object."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _get_pr_summary(branch: str, repo: str) -> dict[str, Any]:
    """Fetch PR and CI data for a branch. Returns gracefully on errors."""
    try:
        pr_data = get_pr_for_branch(branch, repo)
    except Exception:
        pr_data = None

    try:
        ci_data = get_ci_status(repo, branch)
    except Exception:
        ci_data = None

    return {"pr": pr_data, "ci": ci_data}


def _get_ticket_summary(branch: str) -> dict[str, Any]:
    """Extract ticket ID from branch and fetch Linear ticket details. Returns gracefully on errors."""
    ticket_id = extract_ticket_id(branch)
    if not ticket_id:
        return {"ticket_id": None, "details": None}

    try:
        details = get_ticket_details(ticket_id)
    except Exception:
        details = None

    return {"ticket_id": ticket_id, "details": details}


def _is_done(session: dict[str, Any]) -> bool:
    """Heuristic: a session is 'done' if it was last active > 12 hours ago."""
    last_active = _parse_iso_datetime(session["last_active"])
    now = datetime.now(timezone.utc)
    hours_ago = (now - last_active).total_seconds() / 3600
    return hours_ago > 12


def _format_branch_item(
    branch: str,
    pr_summary: dict[str, Any],
    ticket_summary: dict[str, Any],
    is_done: bool,
) -> str:
    """Format a single branch item for the standup report."""
    lines = []

    # Branch name
    lines.append(f"- {branch}")

    # PR info
    pr_data = pr_summary.get("pr")
    if pr_data:
        pr_number = pr_data.get("number")
        if pr_number:
            status_emoji = "✓" if pr_data.get("merged") else "→"
            lines.append(f"  PR #{pr_number} {status_emoji}")

            # Comments info
            comments_count = pr_data.get("comment_count", 0)
            if comments_count > 0:
                latest_comment = pr_data.get("latest_comment_author", "someone")
                lines.append(f"  {comments_count} new comment(s) from {latest_comment}")

            # PR status
            if pr_data.get("merged"):
                lines.append("  ✓ Merged")
            elif pr_data.get("approved"):
                lines.append("  ✓ Approved")
            elif pr_data.get("changes_requested"):
                lines.append("  ⚠ Changes requested")
            else:
                lines.append("  → Awaiting review")

    # CI status
    ci_data = pr_summary.get("ci")
    if ci_data and isinstance(ci_data, dict):
        status = ci_data.get("status", "").lower()
        if status == "success":
            lines.append("  CI → Passing ✓")
        elif status == "failure":
            lines.append("  CI → Failing ✗")
        elif status in ("pending", "in_progress"):
            lines.append("  CI → Running ⏳")

    # Linear ticket info
    ticket_summary_data = ticket_summary.get("details")
    if ticket_summary_data:
        ticket_id = ticket_summary.get("ticket_id")
        if ticket_id:
            title = ticket_summary_data.get("title", "")
            status = ticket_summary_data.get("status", "")
            if title:
                lines.append(f"  {ticket_id}: {title}")
            if status:
                lines.append(f"  Status: {status}")

    return "\n".join(lines)


def generate_standup_report(sessions: list[dict[str, Any]] | None = None) -> str:
    """Generate a formatted standup report from the last 24 hours of activity.

    Args:
        sessions: Optional list of sessions. If None, queries database for last 24h.

    Returns:
        A formatted standup report as a string.
    """
    if sessions is None:
        sessions = get_sessions_last_24h()

    if not sessions:
        # No activity in the last 24 hours
        today = datetime.now().strftime("%B %d, %Y")
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DAILY STANDUP — {today}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

No branch activity in the last 24 hours.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    done_items = []
    in_progress_items = []
    blockers = []

    # Process each session
    for session in sessions:
        branch = session["branch_name"]
        repo = session["repo"]
        is_done_flag = _is_done(session)

        pr_summary = _get_pr_summary(branch, repo)
        ticket_summary = _get_ticket_summary(branch)

        item_text = _format_branch_item(branch, pr_summary, ticket_summary, is_done_flag)

        # Categorize
        if is_done_flag:
            done_items.append(item_text)
        else:
            in_progress_items.append(item_text)

        # Check for blockers
        pr_data = pr_summary.get("pr")
        if pr_data and pr_data.get("changes_requested"):
            blockers.append(f"PR #{pr_data.get('number')} needs revisions")
        if pr_data and not pr_data.get("approved") and pr_data.get("number"):
            blockers.append(f"PR #{pr_data.get('number')} awaiting approval")

    # Format report
    today = datetime.now().strftime("%B %d, %Y")
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 DAILY STANDUP — {today}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    # Done section
    if done_items:
        lines.append("✅ DONE (Yesterday):")
        for item in done_items:
            lines.append(item)
        lines.append("")

    # In progress section
    if in_progress_items:
        lines.append("🔄 IN PROGRESS (Today):")
        for item in in_progress_items:
            lines.append(item)
        lines.append("")

    # Blockers section
    if blockers:
        lines.append("⚠️ BLOCKERS:")
        for blocker in blockers:
            lines.append(f"- {blocker}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using pyperclip. Returns True if successful."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def export_to_file(text: str, filename: str | None = None) -> str | None:
    """Export standup report to a markdown file.

    Args:
        text: The standup report text.
        filename: Optional filename. If None, generates one with today's date.

    Returns:
        The absolute path to the created file, or None if export failed.
    """
    from pathlib import Path

    if filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"standup-{today}.md"

    filepath = Path.cwd() / filename
    try:
        filepath.write_text(text + "\n", encoding="utf-8")
        return str(filepath)
    except Exception:
        return None
