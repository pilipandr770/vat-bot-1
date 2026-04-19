"""
NIS2 Site Audit — Routes
=========================
URL prefix: /nis2/audit/  (registered under existing nis2_bp)

Routes:
  GET  /nis2/audit/              → list of user's audit jobs
  GET  /nis2/audit/new           → form: enter URL
  POST /nis2/audit/start         → create job + start background thread
  GET  /nis2/audit/<job_id>      → job detail + live log
  GET  /nis2/audit/<job_id>/logs → JSON log stream (AJAX polling)
  GET  /nis2/audit/<job_id>/report → full HTML report (inline)
  GET  /nis2/audit/<job_id>/download → standalone HTML report file
"""

from __future__ import annotations

import threading
from datetime import datetime

from flask import (
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from crm.models import db


def _get_client_info() -> dict:
    """Build auditor/client info dict from the logged-in user's registration data."""
    u = current_user
    company = getattr(u, "company_name", None) or u.email
    address = getattr(u, "company_address", None) or ""
    email   = getattr(u, "company_email", None) or u.email
    phone   = getattr(u, "company_phone", None) or getattr(u, "phone", None) or ""
    vat_id  = getattr(u, "company_vat_number", None) or ""
    ust_id  = f"USt-IdNr.: {vat_id}" if vat_id else ""

    return {
        "company": company,
        "address": address,
        "email": email,
        "phone": phone,
        "ust_id": ust_id,
    }


def _run_audit_in_thread(app, job_id: int, target: str) -> None:
    """Run the audit agent in a background thread with proper app context."""
    with app.app_context():
        from app.nis2.models import NIS2AuditJob, NIS2Finding, NIS2AuditLog, NIS2AuditTask
        from app.nis2.site_audit.audit_agent import run_audit
        from app.nis2.site_audit.report_generator import generate_report_html

        def log_fn(level: str, message: str) -> None:
            try:
                entry = NIS2AuditLog(job_id=job_id, level=level, message=message)
                db.session.add(entry)
                db.session.commit()
            except Exception:
                db.session.rollback()

        try:
            # Mark as running
            job = db.session.get(NIS2AuditJob, job_id)
            if not job:
                return
            job.status = "running"
            db.session.commit()

            # Run audit
            result = run_audit(job_id=job_id, target=target, log_fn=log_fn)

            if "error" in result:
                job.status = "failed"
                log_fn("ERROR", result["error"])
                db.session.commit()
                return

            # Persist findings
            for f in result.get("findings", []):
                finding = NIS2Finding(
                    job_id=job_id,
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    severity=f.get("severity", "info"),
                    severity_rank=f.get("severity_rank", 5),
                    cvss=f.get("cvss", ""),
                    dsgvo_article=f.get("dsgvo_article", ""),
                    recommendation=f.get("recommendation", ""),
                    target_url=target,
                    tool=f.get("tool", ""),
                )
                db.session.add(finding)

            # Persist tasks
            for t in result.get("tasks", []):
                done_at = None
                if t.get("done") and t.get("done_at"):
                    try:
                        done_at = datetime.fromisoformat(t["done_at"])
                    except (ValueError, TypeError):
                        done_at = datetime.utcnow()

                task = NIS2AuditTask(
                    job_id=job_id,
                    category=t.get("category", ""),
                    title=t.get("title", ""),
                    description=t.get("description", ""),
                    nis2_ref=t.get("nis2_ref", ""),
                    dsgvo_ref=t.get("dsgvo_ref", ""),
                    required=t.get("required", True),
                    done=t.get("done", False),
                    done_at=done_at,
                    notes=t.get("notes", ""),
                )
                db.session.add(task)

            db.session.commit()

            # Generate HTML report
            # Retrieve all log rows for report
            logs_for_report = [
                {"level": lg.level, "message": lg.message, "created_at": lg.created_at}
                for lg in NIS2AuditLog.query.filter_by(job_id=job_id).order_by(NIS2AuditLog.id).all()
            ]
            findings_for_report = [
                {
                    "title": fn.title,
                    "description": fn.description,
                    "severity": fn.severity,
                    "severity_rank": fn.severity_rank,
                    "cvss": fn.cvss,
                    "dsgvo_article": fn.dsgvo_article,
                    "recommendation": fn.recommendation,
                    "tool": fn.tool,
                }
                for fn in NIS2Finding.query.filter_by(job_id=job_id).order_by(NIS2Finding.severity_rank).all()
            ]
            tasks_for_report = [
                {
                    "category": tk.category,
                    "title": tk.title,
                    "description": tk.description,
                    "nis2_ref": tk.nis2_ref,
                    "dsgvo_ref": tk.dsgvo_ref,
                    "required": tk.required,
                    "done": tk.done,
                    "done_at": tk.done_at.isoformat() if tk.done_at else None,
                    "notes": tk.notes,
                }
                for tk in NIS2AuditTask.query.filter_by(job_id=job_id).order_by(NIS2AuditTask.id).all()
            ]

            # We need client_info — load user
            from auth.models import User
            user = db.session.get(User, job.user_id)
            client_info = {}
            if user:
                company = getattr(user, "company_name", None) or user.email
                address = getattr(user, "company_address", None) or ""
                email   = getattr(user, "company_email", None) or user.email
                phone   = getattr(user, "company_phone", None) or getattr(user, "phone", None) or ""
                vat_id  = getattr(user, "company_vat_number", None) or ""
                ust_id  = f"USt-IdNr.: {vat_id}" if vat_id else ""
                client_info = {
                    "company": company, "address": address,
                    "email": email, "phone": phone, "ust_id": ust_id,
                }

            report_html = generate_report_html(
                target=target,
                client_info=client_info,
                findings=findings_for_report,
                live=result["live"],
                tasks=tasks_for_report,
                logs=logs_for_report,
                tools_used=result.get("tools_used", []),
                inline=False,
            )

            job.report_html = report_html
            job.status = "done"
            job.completed_at = datetime.utcnow()
            db.session.commit()
            log_fn("INFO", "✅ Audit abgeschlossen — Bericht gespeichert")

        except Exception as exc:
            db.session.rollback()
            try:
                job = db.session.get(NIS2AuditJob, job_id)
                if job:
                    job.status = "failed"
                    db.session.commit()
                log_fn("ERROR", f"Unerwarteter Fehler: {exc}")
            except Exception:
                pass


def register_site_audit_routes(bp) -> None:
    """Register all site-audit routes on the nis2 blueprint."""

    # ── List ──────────────────────────────────────────────────────────────
    @bp.route("/audit/")
    def site_audit_index():
        from app.nis2.models import NIS2AuditJob
        jobs = (
            NIS2AuditJob.query
            .filter_by(user_id=current_user.id)
            .order_by(NIS2AuditJob.created_at.desc())
            .limit(20)
            .all()
        )
        return render_template("nis2/site_audit/index.html", jobs=jobs)

    # ── New (form) ─────────────────────────────────────────────────────────
    @bp.route("/audit/new")
    def site_audit_new():
        return render_template("nis2/site_audit/new.html")

    # ── Start ──────────────────────────────────────────────────────────────
    @bp.route("/audit/start", methods=["POST"])
    def site_audit_start():
        from flask import current_app
        from app.nis2.models import NIS2AuditJob
        from app.nis2.site_audit.live_check import is_public_target

        target = (request.form.get("target") or "").strip()
        if not target:
            return jsonify({"error": "Ziel-URL ist erforderlich."}), 400

        # Basic normalisation
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        target = target.rstrip("/")

        # SSRF check
        if not is_public_target(target):
            return jsonify({"error": "Ungültiges oder internes Ziel."}), 400

        job = NIS2AuditJob(
            user_id=current_user.id,
            target=target,
            status="pending",
        )
        db.session.add(job)
        db.session.commit()

        # Run audit in background thread
        app = current_app._get_current_object()  # noqa: SLF001 — needed for thread context
        t = threading.Thread(
            target=_run_audit_in_thread,
            args=(app, job.id, target),
            daemon=True,
        )
        t.start()

        return redirect(url_for("nis2.site_audit_detail", job_id=job.id))

    # ── Detail ─────────────────────────────────────────────────────────────
    @bp.route("/audit/<int:job_id>")
    def site_audit_detail(job_id: int):
        from app.nis2.models import NIS2AuditJob
        job = db.session.get(NIS2AuditJob, job_id)
        if not job or job.user_id != current_user.id:
            abort(404)
        return render_template("nis2/site_audit/detail.html", job=job)

    # ── Log polling (AJAX) ─────────────────────────────────────────────────
    @bp.route("/audit/<int:job_id>/logs")
    def site_audit_logs(job_id: int):
        from app.nis2.models import NIS2AuditJob, NIS2AuditLog
        job = db.session.get(NIS2AuditJob, job_id)
        if not job or job.user_id != current_user.id:
            abort(404)

        since_id = request.args.get("since", 0, type=int)
        entries = (
            NIS2AuditLog.query
            .filter(NIS2AuditLog.job_id == job_id, NIS2AuditLog.id > since_id)
            .order_by(NIS2AuditLog.id)
            .limit(50)
            .all()
        )
        return jsonify({
            "status": job.status,
            "logs": [
                {"id": e.id, "level": e.level, "message": e.message,
                 "ts": e.created_at.strftime("%H:%M:%S") if e.created_at else ""}
                for e in entries
            ],
        })

    # ── Report (inline view) ───────────────────────────────────────────────
    @bp.route("/audit/<int:job_id>/report")
    def site_audit_report(job_id: int):
        from app.nis2.models import NIS2AuditJob
        job = db.session.get(NIS2AuditJob, job_id)
        if not job or job.user_id != current_user.id:
            abort(404)
        if job.status != "done" or not job.report_html:
            return redirect(url_for("nis2.site_audit_detail", job_id=job_id))
        # Return stored HTML report directly
        from flask import Response
        return Response(job.report_html, content_type="text/html; charset=utf-8")

    # ── Download (standalone HTML file) ────────────────────────────────────
    @bp.route("/audit/<int:job_id>/download")
    def site_audit_download(job_id: int):
        from app.nis2.models import NIS2AuditJob
        job = db.session.get(NIS2AuditJob, job_id)
        if not job or job.user_id != current_user.id:
            abort(404)
        if job.status != "done" or not job.report_html:
            abort(404)
        from flask import Response
        filename = f"nis2-audit-{job.id}-{job.target.replace('https://','').replace('http://','').split('/')[0]}.html"
        return Response(
            job.report_html,
            content_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # ── Delete ─────────────────────────────────────────────────────────────
    @bp.route("/audit/<int:job_id>/delete", methods=["POST"])
    def site_audit_delete(job_id: int):
        from app.nis2.models import NIS2AuditJob
        job = db.session.get(NIS2AuditJob, job_id)
        if not job or job.user_id != current_user.id:
            abort(404)
        db.session.delete(job)
        db.session.commit()
        return redirect(url_for("nis2.site_audit_index"))
