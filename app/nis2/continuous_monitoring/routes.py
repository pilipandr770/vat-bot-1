"""
Continuous Compliance Monitoring — Routes

Automated monthly security scans with trend analysis and email alerts.
Reuses WebsiteSecurityScanner from app/pentesting/.
"""

import json
from datetime import datetime, timedelta

from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from crm.models import db

from ..models import MonitoringTarget, MonitoringScan


def register_monitoring_routes(bp):

    @bp.route('/monitoring/')
    @login_required
    def monitoring_dashboard():
        targets = MonitoringTarget.query.filter_by(
            user_id=current_user.id
        ).order_by(MonitoringTarget.created_at.desc()).all()

        # Attach last 2 scans per target for trend display
        for t in targets:
            t.recent_scans = t.scans.limit(5).all()

        return render_template('nis2/monitoring/dashboard.html', targets=targets)

    @bp.route('/monitoring/targets/add', methods=['GET', 'POST'])
    @login_required
    def monitoring_add_target():
        if request.method == 'POST':
            domain = request.form.get('domain', '').strip().lower()
            if not domain:
                flash('Domain darf nicht leer sein.', 'danger')
                return redirect(url_for('nis2.monitoring_add_target'))

            # Normalise — strip scheme
            for prefix in ('https://', 'http://'):
                if domain.startswith(prefix):
                    domain = domain[len(prefix):]
            domain = domain.rstrip('/')

            # Check duplicate
            existing = MonitoringTarget.query.filter_by(
                user_id=current_user.id, domain=domain
            ).first()
            if existing:
                flash(f'Domain „{domain}" wird bereits überwacht.', 'warning')
                return redirect(url_for('nis2.monitoring_dashboard'))

            target = MonitoringTarget(
                user_id=current_user.id,
                domain=domain,
                label=request.form.get('label', '').strip() or domain,
                scan_frequency=request.form.get('scan_frequency', 'monthly'),
                alert_on_degradation=request.form.get('alert_on_degradation') in ('on', '1'),
                alert_threshold=float(request.form.get('alert_threshold', 10)),
                alert_email=request.form.get('alert_email', '').strip() or current_user.email,
                next_scan_at=datetime.utcnow(),   # scan immediately on first add
            )
            db.session.add(target)
            db.session.commit()
            flash(f'Domain „{domain}" wird jetzt überwacht.', 'success')
            return redirect(url_for('nis2.monitoring_scan_now', target_id=target.id))

        return render_template('nis2/monitoring/add_target.html')

    @bp.route('/monitoring/targets/<int:target_id>/scan-now', methods=['POST', 'GET'])
    @login_required
    def monitoring_scan_now(target_id):
        target = MonitoringTarget.query.filter_by(
            id=target_id, user_id=current_user.id
        ).first_or_404()

        from .scanner import run_scan_for_target
        scan = run_scan_for_target(target, triggered_by='manual')

        if scan:
            flash(f'Scan abgeschlossen. Score: {scan.score:.0f}/100', 'success')
        else:
            flash('Scan fehlgeschlagen. Bitte prüfen Sie die Domain.', 'danger')

        return redirect(url_for('nis2.monitoring_target_detail', target_id=target_id))

    @bp.route('/monitoring/targets/<int:target_id>')
    @login_required
    def monitoring_target_detail(target_id):
        target = MonitoringTarget.query.filter_by(
            id=target_id, user_id=current_user.id
        ).first_or_404()

        scans = target.scans.limit(20).all()
        latest = scans[0] if scans else None
        previous = scans[1] if len(scans) > 1 else None
        diff = latest.get_diff() if latest else {}

        return render_template(
            'nis2/monitoring/target_detail.html',
            target=target,
            scans=scans,
            latest=latest,
            previous=previous,
            diff=diff,
        )

    @bp.route('/monitoring/targets/<int:target_id>/delete', methods=['POST'])
    @login_required
    def monitoring_delete_target(target_id):
        target = MonitoringTarget.query.filter_by(
            id=target_id, user_id=current_user.id
        ).first_or_404()
        db.session.delete(target)
        db.session.commit()
        flash('Monitoring-Target gelöscht.', 'info')
        return redirect(url_for('nis2.monitoring_dashboard'))

    @bp.route('/monitoring/api/trend/<int:target_id>')
    @login_required
    def monitoring_trend_api(target_id):
        target = MonitoringTarget.query.filter_by(
            id=target_id, user_id=current_user.id
        ).first_or_404()

        scans = target.scans.order_by(MonitoringScan.scanned_at.asc()).limit(30).all()
        data = {
            'labels': [s.scanned_at.strftime('%d.%m.%Y') for s in scans],
            'scores': [s.score for s in scans],
            'critical': [s.critical_count for s in scans],
            'high': [s.high_count for s in scans],
        }
        return jsonify(data)
