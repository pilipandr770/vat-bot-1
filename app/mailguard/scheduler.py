"""
APScheduler background jobs for MailGuard: poll inboxes, process rules.

Jobs are registered in create_app() and run in a daemon thread so they
don't block the web process.  Errors in individual account polls are
caught and logged; they never crash the scheduler.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def _poll_all_accounts(app) -> None:
    """Iterate all active MailAccount rows and fetch new messages."""
    with app.app_context():
        try:
            from app.mailguard.models import MailAccount
            accounts = MailAccount.query.filter_by(is_active=True).all()
            if not accounts:
                return
            logger.debug('MailGuard poller: checking %d account(s)', len(accounts))
            for acc in accounts:
                try:
                    _poll_single_account(acc)
                except Exception:
                    logger.exception(
                        'MailGuard: failed to poll account id=%s email=%s',
                        acc.id, acc.email
                    )
        except Exception:
            logger.exception('MailGuard poller: unexpected error during poll cycle')


def _poll_single_account(account) -> None:
    """Fetch new messages for a single MailAccount."""
    try:
        if account.provider == 'imap':
            from app.mailguard.connectors.imap import fetch_new_imap
            fetch_new_imap(account)
        else:
            logger.debug(
                'MailGuard: skipping provider=%s for account id=%s',
                account.provider, account.id
            )
    except ImportError:
        logger.warning(
            'MailGuard: IMAP connector not available; skipping account id=%s', account.id
        )


def setup_mailguard_scheduler(app) -> BackgroundScheduler:
    """
    Initialize background poller for MailGuard inboxes.

    Interval is configurable via MAILGUARD_POLL_INTERVAL_MINUTES (default: 5).
    The scheduler is a daemon thread and stops automatically when the process exits.
    """
    interval = int(app.config.get('MAILGUARD_POLL_INTERVAL_MINUTES', 5))
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _poll_all_accounts,
        trigger=IntervalTrigger(minutes=interval),
        args=[app],
        id='mailguard_poll',
        name='MailGuard inbox poller',
        replace_existing=True,
        max_instances=1,   # prevent overlapping runs
        coalesce=True,     # skip missed runs instead of queuing them
    )
    scheduler.start()
    logger.info('MailGuard scheduler started (interval=%d min)', interval)
    return scheduler
