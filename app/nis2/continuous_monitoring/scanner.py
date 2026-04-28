"""
Continuous Monitoring — Scanner

Wraps the existing WebsiteSecurityScanner from app/pentesting/
and persists results as MonitoringScan records with diff analysis.
"""

import json
import logging
from datetime import datetime, timedelta

from crm.models import db
from ..models import MonitoringTarget, MonitoringScan

logger = logging.getLogger(__name__)


def run_scan_for_target(target: MonitoringTarget,
                        triggered_by: str = 'scheduler') -> MonitoringScan | None:
    """
    Run a full security scan for the given target domain and persist results.
    Updates target.last_score, previous_score, last_scan_at, next_scan_at.
    Returns the new MonitoringScan, or None if scan failed.
    """
    from app.pentesting.security_scanner import WebsiteSecurityScanner

    try:
        scanner = WebsiteSecurityScanner(timeout=15)
        raw = scanner.scan_website(target.domain)
    except Exception as exc:
        logger.error('Scan failed for %s: %s', target.domain, exc)
        scan = MonitoringScan(
            target_id=target.id,
            scan_type='full',
            triggered_by=triggered_by,
            error_message=str(exc),
            scanned_at=datetime.utcnow(),
        )
        db.session.add(scan)
        db.session.commit()
        return None

    score = float(raw.get('overall_score', 0))
    checks = raw.get('checks', {})

    # Count findings by severity
    critical = high = medium = low = 0
    for check_name, check_data in checks.items():
        issues = check_data.get('issues', []) if isinstance(check_data, dict) else []
        for issue in issues:
            sev = issue.get('severity', 'low') if isinstance(issue, dict) else 'low'
            if sev == 'critical':
                critical += 1
            elif sev == 'high':
                high += 1
            elif sev == 'medium':
                medium += 1
            else:
                low += 1

    # Build diff vs previous scan
    diff = _build_diff(target, raw)

    # Create scan record
    scan = MonitoringScan(
        target_id=target.id,
        scan_type='full',
        score=score,
        results_json=json.dumps(raw, ensure_ascii=False, default=str),
        diff_json=json.dumps(diff, ensure_ascii=False),
        findings_count=critical + high + medium + low,
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        triggered_by=triggered_by,
        scanned_at=datetime.utcnow(),
    )
    db.session.add(scan)

    # Update target meta
    target.previous_score = target.last_score
    target.last_score = score
    target.last_scan_at = datetime.utcnow()
    target.next_scan_at = _compute_next_scan(target)

    db.session.commit()

    # Send alert if score degraded significantly
    if (target.alert_on_degradation
            and target.previous_score is not None
            and (target.previous_score - score) >= target.alert_threshold):
        _send_degradation_alert(target, scan)

    logger.info('Scan complete: domain=%s score=%.1f findings=%d',
                target.domain, score, scan.findings_count)
    return scan


def _compute_next_scan(target: MonitoringTarget) -> datetime:
    freq_map = {
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30),
        'quarterly': timedelta(days=90),
    }
    delta = freq_map.get(target.scan_frequency, timedelta(days=30))
    return datetime.utcnow() + delta


def _build_diff(target: MonitoringTarget, new_results: dict) -> dict:
    """Compare new scan results against previous scan to highlight changes."""
    prev_scan = MonitoringScan.query.filter_by(target_id=target.id).order_by(
        MonitoringScan.scanned_at.desc()
    ).first()
    if not prev_scan:
        return {'new_scan': True}

    prev_results = prev_scan.get_results()
    prev_checks = prev_results.get('checks', {})
    new_checks = new_results.get('checks', {})

    new_issues = []
    resolved_issues = []

    for check_name in set(list(prev_checks.keys()) + list(new_checks.keys())):
        prev_status = prev_checks.get(check_name, {}).get('status', 'UNKNOWN')
        new_status = new_checks.get(check_name, {}).get('status', 'UNKNOWN')

        if prev_status == 'PASSED' and new_status != 'PASSED':
            new_issues.append({'check': check_name, 'prev': prev_status, 'now': new_status})
        elif prev_status != 'PASSED' and new_status == 'PASSED':
            resolved_issues.append({'check': check_name, 'prev': prev_status, 'now': new_status})

    prev_score = prev_scan.score or 0
    new_score = new_results.get('overall_score', 0)

    return {
        'new_issues': new_issues,
        'resolved_issues': resolved_issues,
        'score_delta': round(new_score - prev_score, 1),
        'prev_score': prev_score,
        'new_score': new_score,
    }


def _send_degradation_alert(target: MonitoringTarget, scan: MonitoringScan):
    """Send email alert when security score degrades beyond threshold."""
    try:
        from flask import current_app
        from flask_mail import Message
        from application import mail

        delta = (target.previous_score or 0) - (scan.score or 0)
        subject = f'[NIS2] Sicherheits-Score für {target.domain} gesunken (-{delta:.0f} Punkte)'
        body = (
            f'Automatische NIS2-Überwachungs-Benachrichtigung\n\n'
            f'Domain: {target.domain}\n'
            f'Vorheriger Score: {target.previous_score:.0f}/100\n'
            f'Aktueller Score:  {scan.score:.0f}/100\n'
            f'Kritische Befunde: {scan.critical_count}\n'
            f'Hohe Befunde:      {scan.high_count}\n\n'
            f'Bitte überprüfen Sie die Details in Ihrem NIS2-Dashboard:\n'
            f'/nis2/monitoring/targets/{target.id}\n\n'
            f'Diese Nachricht wurde automatisch vom NIS2 Compliance Monitor gesendet.'
        )
        msg = Message(subject=subject, recipients=[target.alert_email], body=body)
        mail.send(msg)
        logger.info('Degradation alert sent to %s for %s', target.alert_email, target.domain)
    except Exception as exc:
        logger.warning('Could not send degradation alert: %s', exc)
