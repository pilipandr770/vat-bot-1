# FILE: services/osint_routes.py
import threading
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from .osint.scanner import OsintScanner
from crm.osint_models import db, OsintScan, OsintFinding

osint_bp = Blueprint("osint", __name__, template_folder="../templates")

# ── In-memory store for username scan tasks ───────────────────────────────────
# { task_id: {"status": "pending"|"running"|"done"|"failed",
#              "username": str, "results": list, "error": str, "started_at": dt} }
_username_tasks: dict = {}


# ── Domain / URL / Email OSINT ────────────────────────────────────────────────

@osint_bp.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    if request.method == "POST":
        try:
            url = request.form.get("url") or ""
            domain = request.form.get("domain") or ""
            email = request.form.get("email") or ""

            if not domain:
                return jsonify({"error": "Domain is required"}), 400

            scanner = OsintScanner(url=url, domain=domain, email=email)
            results = scanner.run_all()

            scan_obj = OsintScan(url=url or None, domain=domain or None, email=email or None)
            db.session.add(scan_obj)
            db.session.flush()

            for r in results:
                f = OsintFinding(
                    scan_id=scan_obj.id,
                    service=r.get("service"),
                    status=r.get("status"),
                    notes=r.get("notes", ""),
                    data=r.get("data") or {},
                )
                db.session.add(f)
            db.session.commit()

            return jsonify({"scan_id": scan_obj.id, "results": results})

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    return render_template("admin/osint_scan.html")


@osint_bp.route("/scan/<int:scan_id>")
@login_required
def scan_view(scan_id: int):
    scan_obj = OsintScan.query.get_or_404(scan_id)
    return render_template("admin/osint_results.html", scan=scan_obj)


# ── Username OSINT ────────────────────────────────────────────────────────────

def _run_username_scan(task_id: str, username: str) -> None:
    """Background thread: check username on all platforms, store result in task dict."""
    from .osint.adapters.username_adapter import check_username
    _username_tasks[task_id]["status"] = "running"
    try:
        results = check_username(username)
        _username_tasks[task_id]["status"] = "done"
        _username_tasks[task_id]["results"] = results
    except Exception as exc:
        _username_tasks[task_id]["status"] = "failed"
        _username_tasks[task_id]["error"] = str(exc)


@osint_bp.route("/username-scan", methods=["POST"])
@login_required
def username_scan_start():
    """Start async username scan. Returns task_id immediately."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lstrip("@")
    if not username:
        return jsonify({"error": "Username is required"}), 400
    if len(username) > 50:
        return jsonify({"error": "Username too long"}), 400

    task_id = str(uuid.uuid4())
    _username_tasks[task_id] = {
        "status": "pending",
        "username": username,
        "results": [],
        "error": None,
        "started_at": datetime.utcnow().isoformat(),
    }

    t = threading.Thread(
        target=_run_username_scan,
        args=(task_id, username),
        daemon=True,
    )
    t.start()

    return jsonify({"task_id": task_id, "status": "pending"}), 202


@osint_bp.route("/username-scan/result/<task_id>")
@login_required
def username_scan_result(task_id: str):
    """Poll for username scan result."""
    task = _username_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task["status"] in ("pending", "running"):
        return jsonify({"status": task["status"]}), 200

    if task["status"] == "done":
        found = [r for r in task["results"] if r["status"] == "found"]
        return jsonify({
            "status": "done",
            "username": task["username"],
            "results": task["results"],
            "found_count": len(found),
            "total": len(task["results"]),
        }), 200

    return jsonify({"status": "failed", "error": task.get("error", "Unknown error")}), 200
