"""
Background Scheduler - Daily monitoring tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from services.monitoring import monitoring_service
from services.alerts import alert_service
import logging

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Background scheduler for automated monitoring tasks"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("MonitoringScheduler initialized")
    
    def setup_jobs(self):
        """Setup all scheduled jobs"""
        
        # Daily monitoring check at 02:00 AM
        self.scheduler.add_job(
            func=self.daily_monitoring_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_monitoring',
            name='Daily Counterparty Monitoring Check',
            replace_existing=True
        )
        logger.info("Job 'daily_monitoring' scheduled for 02:00 AM daily")
        
        # Send alert emails at 08:00 AM
        self.scheduler.add_job(
            func=self.send_alerts_job,
            trigger=CronTrigger(hour=8, minute=0),
            id='send_alerts',
            name='Send Alert Emails',
            replace_existing=True
        )
        logger.info("Job 'send_alerts' scheduled for 08:00 AM daily")
        
        # Optional: Additional check at 14:00 PM
        self.scheduler.add_job(
            func=self.daily_monitoring_job,
            trigger=CronTrigger(hour=14, minute=0),
            id='afternoon_monitoring',
            name='Afternoon Counterparty Monitoring Check',
            replace_existing=True
        )
        logger.info("Job 'afternoon_monitoring' scheduled for 14:00 PM daily")
    
    def daily_monitoring_job(self):
        """Daily monitoring check job"""
        try:
            logger.info("Starting daily monitoring job...")
            monitoring_service.run_daily_checks()
            logger.info("Daily monitoring job completed successfully")
        except Exception as e:
            logger.error(f"Daily monitoring job failed: {str(e)}", exc_info=True)
    
    def send_alerts_job(self):
        """Send pending alerts job"""
        try:
            logger.info("Starting alert sending job...")
            if alert_service:
                alert_service.send_pending_alerts()
                logger.info("Alert sending job completed successfully")
            else:
                logger.warning("Alert service not initialized, skipping alert sending")
        except Exception as e:
            logger.error(f"Alert sending job failed: {str(e)}", exc_info=True)
    
    def shutdown(self):
        """Shutdown scheduler"""
        self.scheduler.shutdown()
        logger.info("MonitoringScheduler shut down")
    
    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()

# Global scheduler instance
scheduler = None

def init_scheduler():
    """Initialize scheduler"""
    global scheduler
    scheduler = MonitoringScheduler()
    scheduler.setup_jobs()
    return scheduler

def get_scheduler():
    """Get scheduler instance"""
    return scheduler
