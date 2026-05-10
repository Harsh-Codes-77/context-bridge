"""Local web dashboard for context-bridge.

Serves session history and allows triggering a fresh context fetch via API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, abort, jsonify, render_template, request

from cli.main import run_status_logic
from storage.db import get_all_sessions, get_cache_with_meta, delete_session, delete_old_sessions


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
            repo = str(session.get("repo", "")).strip()

            github_cache = get_cache_with_meta(branch_name, "github", max_age_minutes=720)
            linear_cache = get_cache_with_meta(branch_name, "linear", max_age_minutes=720)
            slack_cache = get_cache_with_meta(branch_name, "slack", max_age_minutes=720)

            github_content = github_cache.get("content") if github_cache else {}
            linear_content = linear_cache.get("content") if linear_cache else {}
            slack_content = slack_cache.get("content") if slack_cache else {}

            session["github"] = github_content
            session["linear"] = linear_content
            session["slack"] = slack_content
            session["context_meta"] = {
                "github": github_cache,
                "linear": linear_cache,
                "slack": slack_cache,
            }

            # Extract URLs from cached integration data
            # GitHub PR URL
            pr_data = github_content.get("pr", {})
            pr_number = pr_data.get("number")
            pr_url = pr_data.get("url")
            session["pr_number"] = pr_number
            session["pr_url"] = pr_url

            # GitHub Actions (CI) URL
            ci_url = None
            if repo:
                ci_url = f"https://github.com/{repo}/actions"
            session["ci_url"] = ci_url

            # Linear ticket URL
            linear_data = linear_content.get("ticket_id") if linear_content else None
            ticket_id = linear_data if isinstance(linear_data, str) else None
            ticket_url = None
            if ticket_id:
                # Construct Linear ticket URL from ticket_id (e.g., "CON-5" → "https://linear.app/...")
                # Linear ticket URL format: https://linear.app/team-slug/issue/CON-5
                # Since we don't have team slug, we use the identifier directly
                ticket_url = f"https://linear.app/issue/{ticket_id}"
            session["ticket_id"] = ticket_id
            session["ticket_url"] = ticket_url

            # GitHub repo URL
            repo_url = None
            if repo:
                repo_url = f"https://github.com/{repo}"
            session["repo_url"] = repo_url

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

    @app.get("/api/search")
    def api_search():
        """Search sessions by branch name, repo name, or files touched.
        
        Query parameters:
          q: search query string (case-insensitive)
        
        Returns filtered sessions matching the query.
        """
        query = request.args.get("q", "").strip().lower()
        if not query:
            sessions = get_all_sessions()
        else:
            sessions = get_all_sessions()
            filtered = []
            for session in sessions:
                branch_name = str(session.get("branch_name", "")).lower()
                repo = str(session.get("repo", "")).lower()
                files_touched = session.get("files_touched", [])
                if not isinstance(files_touched, list):
                    files_touched = []
                files_str = " ".join(str(f).lower() for f in files_touched)
                
                # Match if query found in branch, repo, or files
                if (query in branch_name or 
                    query in repo or 
                    query in files_str):
                    filtered.append(session)
            sessions = filtered
        
        return jsonify({
            "ok": True,
            "query": request.args.get("q", ""),
            "count": len(sessions),
            "sessions": sessions,
        })

    @app.delete("/api/sessions/<path:branch_name>")
    def delete_branch_session(branch_name: str):
        """Delete a session by branch name.
        
        Parameters:
          branch_name: URL-encoded branch name (supports slashes via path converter)
        
        Returns 404 if the branch was not found.
        """
        try:
            branch_name = unquote(branch_name)
            deleted = delete_session(branch_name)
            
            if deleted == 0:
                return jsonify({"success": False, "error": "Branch not found"}), 404
            
            return jsonify({"success": True, "deleted": branch_name})
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.delete("/api/sessions/cleanup")
    def cleanup_old_sessions():
        """Delete all sessions older than the specified number of days.
        
        Query parameters:
          days: Age threshold in days (default: 30)
        
        Returns the count of deleted sessions.
        """
        try:
            days = request.args.get("days", "30", type=int)
            if days < 0:
                return jsonify({"success": False, "error": "days must be >= 0"}), 400
            
            deleted_count = delete_old_sessions(days)
            return jsonify({"success": True, "deleted_count": deleted_count})
        except (ValueError, TypeError) as e:
            return jsonify({"success": False, "error": str(e)}), 400

    return app


def run_dashboard() -> None:
    """Run dashboard server on localhost:4242 only."""
    app = create_app()
    app.run(host="127.0.0.1", port=4242, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_dashboard()
