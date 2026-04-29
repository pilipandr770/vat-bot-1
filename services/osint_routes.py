# FILE: services/osint_routes.py
import json
import threading
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import login_required

from .osint.scanner import OsintScanner
from crm.osint_models import db, OsintScan, OsintFinding

osint_bp = Blueprint("osint", __name__, template_folder="../templates")

_USERNAME_TASK_TTL = 3600  # 1 hour


def _task_key(task_id: str) -> str:
    return f"username_scan:{task_id}"


def _save_task(task_id: str, data: dict) -> None:
    try:
        import redis as _redis
        r = _redis.from_url(current_app.config.get('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
        r.setex(_task_key(task_id), _USERNAME_TASK_TTL, json.dumps(data, default=str))
    except Exception:
        pass


def _load_task(task_id: str) -> dict | None:
    try:
        import redis as _redis
        r = _redis.from_url(current_app.config.get('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
        raw = r.get(_task_key(task_id))
        return json.loads(raw) if raw else None
    except Exception:
        return None


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

def _run_username_scan(task_id: str, username: str, app) -> None:
    """Background thread: check username progressively, saving each result to Redis."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .osint.adapters.username_adapter import PLATFORMS, _check_one

    with app.app_context():
        task = _load_task(task_id) or {}
        task["status"] = "running"
        task["total"] = len(PLATFORMS)
        _save_task(task_id, task)

        try:
            with ThreadPoolExecutor(max_workers=15) as pool:
                futures = {pool.submit(_check_one, username, p): p for p in PLATFORMS}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception:
                        p = futures[future]
                        result = {
                            "platform": p["name"],
                            "category": p["category"],
                            "url": p["url"].format(username=username),
                            "status": "unknown",
                        }
                    task["results"].append(result)
                    task["checked"] = len(task["results"])
                    _save_task(task_id, task)

            order = {"found": 0, "not_found": 1, "unknown": 2}
            task["results"].sort(
                key=lambda r: (order.get(r["status"], 9), r["category"], r["platform"])
            )
            task["status"] = "done"
            _save_task(task_id, task)
        except Exception as exc:
            task["status"] = "failed"
            task["error"] = str(exc)
            _save_task(task_id, task)


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
    task_data = {
        "status": "pending",
        "username": username,
        "results": [],
        "checked": 0,
        "total": 0,
        "error": None,
        "started_at": datetime.utcnow().isoformat(),
    }
    _save_task(task_id, task_data)

    app = current_app._get_current_object()
    t = threading.Thread(
        target=_run_username_scan,
        args=(task_id, username, app),
        daemon=True,
    )
    t.start()

    return jsonify({"task_id": task_id, "status": "pending"}), 202


@osint_bp.route("/username-scan/result/<task_id>")
@login_required
def username_scan_result(task_id: str):
    """Poll for username scan result."""
    task = _load_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task["status"] in ("pending", "running"):
        found_so_far = [r for r in task["results"] if r["status"] == "found"]
        return jsonify({
            "status": task["status"],
            "checked": task.get("checked", 0),
            "total": task.get("total", 0),
            "results": task["results"],
            "found_count": len(found_so_far),
        }), 200

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
