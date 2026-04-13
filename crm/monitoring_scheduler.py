"""
APScheduler background job for daily CRM monitoring.

Runs the existing monitoring service logic on a configurable schedule
(default: 03:00 AM daily).  The existing MonitoringScheduler in
services/scheduler.py handles its own jobs; this module adds a
separate scheduler limited to CRM counterparty re-checks.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _run_daily_monitoring(app) -> None:
    """Run one CRM monitoring cycle inside the app context."""
    with app.app_context():
        try:
            from crm.monitor import MonitoringService
            service = MonitoringService()
            result = service.run_daily_monitoring()
            logger.info(
                'CRM monitoring cycle complete: checked=%s changes=%s alerts=%s',
                result.get('total_checks_monitored', 0),
                result.get('changes_detected', 0),
                result.get('alerts_created', 0),
            )
        except Exception:
            logger.exception('CRM monitoring cycle failed')


def init_monitoring_scheduler(app) -> BackgroundScheduler:
    """
    Initialize the daily CRM counterparty monitoring scheduler.

    Schedule is configurable via CRM_MONITORING_HOUR (0-23, default: 3).
    Returns the started BackgroundScheduler so the caller can attach it
    to the app object for lifecycle management.
    """
    hour = int(app.config.get('CRM_MONITORING_HOUR', 3))
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _run_daily_monitoring,
        trigger=CronTrigger(hour=hour, minute=0),
        args=[app],
        id='crm_daily_monitoring',
        name='CRM daily counterparty re-check',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info('CRM monitoring scheduler started (daily at %02d:00)', hour)
    return scheduler
