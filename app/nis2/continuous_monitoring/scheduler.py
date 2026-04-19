"""
Continuous Monitoring — APScheduler Background Job

Runs daily at 02:00 and scans all active targets whose next_scan_at is due.
Pattern mirrors crm/monitoring_scheduler.py.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def init_nis2_monitoring_scheduler(app) -> BackgroundScheduler:
    """
    Start the NIS2 continuous monitoring scheduler.
    Runs daily at 02:00 AM (configurable via NIS2_MONITORING_HOUR).
    Returns the started scheduler so the caller can store it on app.
    """
    hour = int(app.config.get('NIS2_MONITORING_HOUR', 2))
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _run_due_scans,
        trigger=CronTrigger(hour=hour, minute=0),
        args=[app],
        id='nis2_continuous_monitoring',
        name='NIS2 Continuous Compliance Monitoring',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info('NIS2 monitoring scheduler started (daily at %02d:00)', hour)
    return scheduler


def _run_due_scans(app) -> None:
    """Check all active targets and scan those whose next_scan_at has arrived."""
    with app.app_context():
        from .models import MonitoringTarget  # local import to avoid circular
        try:
            from app.nis2.models import MonitoringTarget as MT
        except ImportError:
            return

        now = datetime.utcnow()
        due_targets = MT.query.filter(
            MT.is_active == True,
            (MT.next_scan_at <= now) | (MT.next_scan_at == None),
        ).all()

        if not due_targets:
            logger.debug('NIS2 monitoring: no targets due for scan')
            return

        logger.info('NIS2 monitoring: scanning %d due target(s)', len(due_targets))

        from app.nis2.continuous_monitoring.scanner import run_scan_for_target
        for target in due_targets:
            try:
                run_scan_for_target(target, triggered_by='scheduler')
            except Exception:
                logger.exception('Scheduled scan failed for target %d (%s)',
                                 target.id, target.domain)
