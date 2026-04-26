"""Slack integration utilities for context-bridge.

Fetches recent relevant Slack messages using Slack search API.
"""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


try:
    from config import get_slack_token
except Exception as exc:  # pragma: no cover - depends on local env setup
    get_slack_token = None
    _CONFIG_IMPORT_ERROR = exc
else:
    _CONFIG_IMPORT_ERROR = None


SLACK_API_BASE = "https://slack.com/api"
REQUEST_TIMEOUT_SECONDS = 20
console = Console()


def _require_token() -> str:
    """Return a usable Slack token or raise a helpful error."""
    token_error: Exception | None = None

    if get_slack_token is not None:
        try:
            return get_slack_token()
        except Exception as exc:
            token_error = exc

    load_dotenv()
    env_token = os.getenv("SLACK_TOKEN")
    if env_token:
        return env_token.strip()

    if token_error is not None:
        raise RuntimeError(str(token_error)) from token_error

    if _CONFIG_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Could not read SLACK_TOKEN from config.py. "
            "Run 'cb init' to configure tokens."
        ) from _CONFIG_IMPORT_ERROR

    raise RuntimeError("Missing SLACK_TOKEN. Run 'cb init' to configure tokens.")


def _slack_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """Perform a Slack API GET call and return JSON payload."""
    token = _require_token()
    url = f"{SLACK_API_BASE}{path}"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise RuntimeError(f"Slack API request failed for {url}: {exc}") from exc

    if response.status_code in (401, 403):
        raise RuntimeError("Slack auth failed. Check your SLACK_TOKEN and token scopes.")

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RuntimeError(f"Slack API rate limit reached. Retry after ~{retry_after}s.")

    if not response.ok:
        raise RuntimeError(f"Slack API returned HTTP {response.status_code}: {response.text}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Slack API returned non-JSON response.") from exc

    if not payload.get("ok"):
        err = payload.get("error", "unknown_error")
        needed = payload.get("needed")
        provided = payload.get("provided")
        if needed or provided:
            raise RuntimeError(
                f"Slack API error: {err} (needed: {needed or 'n/a'}, provided: {provided or 'n/a'})"
            )
        raise RuntimeError(f"Slack API error: {err}")

    return payload


def _build_query(branch_name: str, ticket_id: str | None) -> str:
    """Build a Slack search query from branch and ticket context."""
    terms: list[str] = []
    if ticket_id:
        terms.append(ticket_id)
    if branch_name:
        terms.append(branch_name)

    return " OR ".join(term for term in terms if term)


def _build_terms(branch_name: str, ticket_id: str | None) -> list[str]:
    """Build normalized search terms for fallback matching."""
    terms: list[str] = []
    if ticket_id:
        terms.append(ticket_id.strip())
    if branch_name:
        terms.append(branch_name.strip())
    return [term for term in terms if term]


def _normalize_message(item: dict[str, Any], channel_name: str) -> dict[str, str]:
    """Normalize Slack payload entries into a common message shape."""
    username = item.get("username") or item.get("user") or "Unknown"
    raw_text = (item.get("text") or "").replace("\n", " ").strip()
    text = raw_text[:180] + ("..." if len(raw_text) > 180 else "")
    return {
        "author": str(username),
        "channel": channel_name or "unknown-channel",
        "text": text,
        "permalink": item.get("permalink") or "",
        "timestamp": str(item.get("ts") or ""),
    }


def _search_messages_api(query: str, max_messages: int) -> list[dict[str, str]]:
    """Fetch messages via search.messages API."""
    payload = _slack_get(
        "/search.messages",
        {
            "query": query,
            "count": max(1, min(20, max_messages)),
            "sort": "timestamp",
            "sort_dir": "desc",
        },
    )

    matches = ((payload.get("messages") or {}).get("matches") or [])[:max_messages]
    messages: list[dict[str, str]] = []
    for item in matches:
        channel_data = item.get("channel") or {}
        channel_name = channel_data.get("name") or "unknown-channel"
        messages.append(_normalize_message(item, channel_name))
    return messages


def _history_fallback(terms: list[str], max_messages: int) -> list[dict[str, str]]:
    """Fallback for bot tokens: scan channel histories for matching terms."""
    channels_payload = _slack_get(
        "/conversations.list",
        {
            "limit": 200,
            "types": "public_channel",
        },
    )
    channels = channels_payload.get("channels") or []
    lowered_terms = [term.lower() for term in terms]

    matches: list[dict[str, str]] = []
    for channel in channels[:80]:
        channel_id = channel.get("id")
        channel_name = channel.get("name") or "unknown-channel"
        if not channel_id:
            continue

        try:
            history_payload = _slack_get(
                "/conversations.history",
                {
                    "channel": channel_id,
                    "limit": 60,
                },
            )
        except Exception:
            continue  # Skip channels the bot cannot access

        for message in history_payload.get("messages") or []:
            text = str(message.get("text") or "")
            lowered_text = text.lower()
            if any(term in lowered_text for term in lowered_terms):
                matches.append(_normalize_message(message, channel_name))

    matches.sort(key=lambda item: float(item.get("timestamp") or 0), reverse=True)
    return matches[:max_messages]


def get_recent_messages(
    branch_name: str,
    ticket_id: str | None,
    max_messages: int = 5,
) -> dict[str, Any]:
    """Fetch relevant Slack messages for the current branch/ticket context."""
    query = _build_query(branch_name, ticket_id)
    terms = _build_terms(branch_name, ticket_id)
    if not query:
        return {
            "query": "",
            "messages": [],
            "reason": "No branch or ticket query available",
            "source": "none",
        }

    search_error: str | None = None
    try:
        messages = _search_messages_api(query, max_messages)
        return {
            "query": query,
            "messages": messages,
            "source": "search.messages",
        }
    except Exception as exc:
        search_error = str(exc)

    # Fallback for bot tokens where search.messages may be unavailable.
    try:
        messages = _history_fallback(terms, max_messages)
        return {
            "query": query,
            "messages": messages,
            "source": "conversations.history",
            "warning": f"search.messages unavailable: {search_error}",
        }
    except Exception as fallback_exc:
        raise RuntimeError(
            f"Slack lookup failed. search error: {search_error}; "
            f"history fallback error: {fallback_exc}"
        ) from fallback_exc


def display_slack_summary(branch_name: str, ticket_id: str | None) -> None:
    """Print a compact Slack summary panel for branch/ticket context."""
    try:
        summary = get_recent_messages(branch_name, ticket_id, max_messages=3)
    except Exception as exc:
        console.print(f"[bold red]Slack summary failed:[/bold red] {exc}")
        return

    messages = summary.get("messages", [])
    if not messages:
        messages_text = "No recent matching messages"
    else:
        lines = []
        for msg in messages:
            lines.append(
                f"- [bold]{msg.get('author', 'Unknown')}[/bold] "
                f"in #{msg.get('channel', 'unknown')}: {msg.get('text', '')}"
            )
        messages_text = "\n".join(lines)

    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("Query", summary.get("query", ""))
    table.add_row("Source", summary.get("source", "unknown"))
    if summary.get("warning"):
        table.add_row("Warning", str(summary.get("warning")))
    table.add_row("Messages", messages_text)

    panel = Panel(
        table,
        title="[bold blue]Slack Context Summary[/bold blue]",
        border_style="bright_blue",
        expand=False,
    )
    console.print(panel)
