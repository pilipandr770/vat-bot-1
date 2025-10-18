# FILE: services/osint_routes.py
from flask import Blueprint, request, render_template, jsonify
from flask_login import login_required
from .osint.scanner import OsintScanner
from crm.osint_models import db, OsintScan, OsintFinding

osint_bp = Blueprint("osint", __name__, template_folder="../templates")


@osint_bp.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    if request.method == "POST":
        url = request.form.get("url") or ""
        domain = request.form.get("domain") or ""
        email = request.form.get("email") or ""
        scanner = OsintScanner(url=url, domain=domain, email=email)
        results = scanner.run_all()

        scan = OsintScan(url=url or None, domain=domain or None, email=email or None)
        db.session.add(scan)
        db.session.flush()

        for r in results:
            f = OsintFinding(
                scan_id=scan.id,
                service=r.get("service"),
                status=r.get("status"),
                notes=r.get("notes", ""),
                data=r.get("data") or {},
            )
            db.session.add(f)
        db.session.commit()

        return jsonify({"scan_id": scan.id, "results": results})

    return render_template("admin/osint_scan.html")


@osint_bp.route("/scan/<int:scan_id>")
def scan_view(scan_id: int):
    scan = OsintScan.query.get_or_404(scan_id)
    return render_template("admin/osint_results.html", scan=scan)
