"""Local web dashboard for context-bridge.

Serves session history and allows triggering a fresh context fetch via API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

from cli.main import run_status_logic
from storage.db import get_all_sessions, get_cache_with_meta


LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _is_local_request(remote_addr: str | None) -> bool:
    """Allow only loopback requests."""
    if not remote_addr:
        return True
    if remote_addr in LOCAL_HOSTS:
        return True
    if remote_addr.startswith("::ffff:127."):
        return True
    return False


def create_app() -> Flask:
    """Create and configure the Flask application."""
    template_dir = Path(__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    @app.before_request
    def _restrict_to_localhost() -> None:
        if not _is_local_request(request.remote_addr):
            abort(403)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/sessions")
    def api_sessions():
        sessions = get_all_sessions()

        for session in sessions:
            branch_name = str(session.get("branch_name", "")).strip()

            github_cache = get_cache_with_meta(branch_name, "github", max_age_minutes=720)
            linear_cache = get_cache_with_meta(branch_name, "linear", max_age_minutes=720)
            slack_cache = get_cache_with_meta(branch_name, "slack", max_age_minutes=720)

            session["github"] = github_cache.get("content") if github_cache else {}
            session["linear"] = linear_cache.get("content") if linear_cache else {}
            session["slack"] = slack_cache.get("content") if slack_cache else {}
            session["context_meta"] = {
                "github": github_cache,
                "linear": linear_cache,
                "slack": slack_cache,
            }

        return jsonify(
            {
                "ok": True,
                "count": len(sessions),
                "server_time": datetime.now(timezone.utc).isoformat(),
                "sessions": sessions,
            }
        )

    @app.get("/api/status")
    def api_status():
        try:
            data = run_status_logic(interactive=False, render=False)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, **data})

    return app


def run_dashboard() -> None:
    """Run dashboard server on localhost:4242 only."""
    app = create_app()
    app.run(host="127.0.0.1", port=4242, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_dashboard()
