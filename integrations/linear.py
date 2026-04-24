"""Linear integration utilities for context-bridge.

This module extracts ticket IDs from branch names, fetches issue details from
Linear's GraphQL API, and renders a compact terminal summary.

How to get a Linear API token:
1. Open Linear.
2. Go to Settings -> API.
3. Create a Personal API key.
4. Put it in your .env as LINEAR_TOKEN=your_key.
"""

from __future__ import annotations

import os
import re
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Use lazy config getter so unrelated missing tokens do not break imports.
try:
    from config import get_linear_token
except Exception as exc:  # pragma: no cover - depends on local env setup
    get_linear_token = None
    _CONFIG_IMPORT_ERROR = exc
else:
    _CONFIG_IMPORT_ERROR = None


LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
REQUEST_TIMEOUT_SECONDS = 20
TICKET_PATTERN = re.compile(r"(?:^|[/_-])([A-Za-z][A-Za-z0-9]+-\d+)(?=-|$)", re.IGNORECASE)
console = Console()


def _require_token() -> str:
    """Return a usable Linear token or raise a helpful error."""
    token_error: Exception | None = None

    if get_linear_token is not None:
        try:
            return get_linear_token()
        except Exception as exc:
            token_error = exc

    # Fallback keeps this module usable even if config.py import fails.
    load_dotenv()
    env_token = os.getenv("LINEAR_TOKEN")
    if env_token:
        return env_token

    if token_error is not None:
        raise RuntimeError(str(token_error)) from token_error

    if _CONFIG_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Could not read LINEAR_TOKEN from config.py. "
            "Run 'cb init' to configure tokens."
        ) from _CONFIG_IMPORT_ERROR

    raise RuntimeError("Missing LINEAR_TOKEN. Run 'cb init' to configure tokens.")


def _linear_query(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Send a GraphQL query to Linear and return the data payload."""
    token = _require_token()
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            LINEAR_GRAPHQL_URL,
            headers=headers,
            json={"query": query, "variables": variables},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Linear API request failed: {exc}") from exc

    if response.status_code in (401, 403):
        raise RuntimeError("Linear auth failed. Verify LINEAR_TOKEN permissions.")

    if not response.ok:
        raise RuntimeError(
            f"Linear API returned HTTP {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Linear API returned non-JSON response.") from exc

    errors = payload.get("errors") or []
    if errors:
        combined = "; ".join(err.get("message", "Unknown GraphQL error") for err in errors)
        raise RuntimeError(f"Linear GraphQL error: {combined}")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Linear API response missing data payload.")

    return data


def _priority_label(value: Any) -> str:
    """Convert Linear numeric priority to a human-friendly label."""
    mapping = {
        0: "No priority",
        1: "Urgent",
        2: "High",
        3: "Medium",
        4: "Low",
    }
    return mapping.get(value, "Unknown")


def _status_color(status_name: str, status_type: str) -> str:
    """Pick status color for terminal display."""
    lowered_name = (status_name or "").lower()
    lowered_type = (status_type or "").lower()

    if "block" in lowered_name:
        return "red"
    if lowered_type == "completed" or "done" in lowered_name:
        return "green"
    if lowered_type == "started" or "progress" in lowered_name:
        return "yellow"
    return "white"


def extract_ticket_id(branch_name: str) -> str | None:
    """Extract a ticket identifier from a branch name (case-insensitive).

    The matched ID is always uppercased so the Linear API receives the
    canonical form (e.g. ``CON-5``, not ``con-5``).

    Examples::

        con-5-login-timeout-after-30s   → CON-5
        fix/AUTH-1-login-timeout         → AUTH-1
        feature/FEAT-23-dark-mode        → FEAT-23
        pharshpathak703/con-5-something  → CON-5
    """
    if not branch_name:
        return None

    match = TICKET_PATTERN.search(branch_name)
    return match.group(1).upper() if match else None


def get_ticket_details(ticket_id: str) -> dict[str, Any]:
    """Fetch issue details from Linear GraphQL and return normalized fields.

    Returns a dict with:
    - ticket_id
    - title
    - status
    - status_type
    - assignee
    - description
    - priority
    - comments (up to last 3)
    """
    if not ticket_id:
        raise ValueError("ticket_id is required")

    # Primary query: fetch issue by identifier/id with all requested fields.
    issue_query = """
    query GetIssue($ticketId: String!) {
      issue(id: $ticketId) {
        identifier
        title
        description
        priority
        state {
          name
          type
        }
        assignee {
          name
        }
        comments(first: 3) {
          nodes {
            body
            createdAt
            user {
              name
            }
          }
        }
      }
    }
    """

    data = _linear_query(issue_query, {"ticketId": ticket_id})
    issue = data.get("issue")

    if not issue:
        raise RuntimeError(
            f"Ticket {ticket_id} was not found in Linear or is not accessible."
        )

    state = issue.get("state") or {}
    assignee = issue.get("assignee") or {}
    comments_nodes = ((issue.get("comments") or {}).get("nodes") or [])[:3]

    comments: list[dict[str, str]] = []
    for item in comments_nodes:
        user = item.get("user") or {}
        comments.append(
            {
                "author": user.get("name", "Unknown"),
                "body": item.get("body", ""),
                "created_at": item.get("createdAt", ""),
            }
        )

    return {
        "ticket_id": issue.get("identifier", ticket_id),
        "title": issue.get("title", "Untitled"),
        "status": state.get("name", "Unknown"),
        "status_type": state.get("type", ""),
        "assignee": assignee.get("name", "Unassigned"),
        "description": issue.get("description", ""),
        "priority": _priority_label(issue.get("priority")),
        "comments": comments,
    }


def display_linear_summary(branch_name: str) -> None:
    """Show a rich summary for the Linear ticket inferred from branch name."""
    ticket_id = extract_ticket_id(branch_name)
    if not ticket_id:
        console.print(
            "[yellow]No Linear ticket ID found in branch name. "
            "Expected format like AUTH-412 or FEAT-23.[/yellow]"
        )
        return

    try:
        details = get_ticket_details(ticket_id)
    except Exception as exc:
        console.print(f"[bold red]Linear summary failed:[/bold red] {exc}")
        return

    status = details.get("status", "Unknown")
    status_type = details.get("status_type", "")
    color = _status_color(status, status_type)
    status_markup = f"[{color}]{status}[/{color}]"

    comments = details.get("comments", [])[:2]
    if comments:
        comment_lines = []
        for item in comments:
            author = item.get("author", "Unknown")
            body = (item.get("body", "") or "").strip().replace("\n", " ")
            snippet = body[:120] + ("..." if len(body) > 120 else "")
            comment_lines.append(f"- [bold]{author}[/bold]: {snippet}")
        comments_text = "\n".join(comment_lines)
    else:
        comments_text = "No recent comments"

    summary = Table.grid(padding=(0, 1))
    summary.add_column(style="bold cyan", no_wrap=True)
    summary.add_column()
    summary.add_row("Ticket", details.get("ticket_id", ticket_id))
    summary.add_row("Title", details.get("title", "Untitled"))
    summary.add_row("Status", status_markup)
    summary.add_row("Assignee", details.get("assignee", "Unassigned"))
    summary.add_row("Priority", details.get("priority", "Unknown"))
    summary.add_row("Comments", comments_text)

    panel = Panel(
        summary,
        title="[bold blue]Linear Ticket Summary[/bold blue]",
        border_style="bright_blue",
        expand=False,
    )
    console.print(panel)