"""
Background Scheduler - Daily monitoring tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from services.monitoring import monitoring_service
from services.alerts import alert_service
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Background scheduler for automated monitoring tasks"""
    
    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler()
        self._app = app
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
        
        # Update European scam databases weekly on Sunday at 03:00 AM
        self.scheduler.add_job(
            func=self.update_european_scam_db_job,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='update_european_scam_db',
            name='Update European Scam Databases',
            replace_existing=True
        )
        logger.info("Job 'update_european_scam_db' scheduled for Sunday 03:00 AM weekly")
        
        # Daily blog post generation at 07:00 AM
        # misfire_grace_time=21600 → fires even if app was sleeping, up to 6 hours late
        self.scheduler.add_job(
            func=self.generate_blog_post_job,
            trigger=CronTrigger(hour=7, minute=0),
            id='generate_blog_post',
            name='Generate Daily SEO Blog Post',
            replace_existing=True,
            misfire_grace_time=21600,  # 6 hours grace — handles Render cold starts
            coalesce=True,             # run once even if multiple misfires stacked up
        )
        logger.info("Job 'generate_blog_post' scheduled for 07:00 AM daily")
        
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
    
    def update_european_scam_db_job(self):
        """Update European scam phone databases job"""
        try:
            logger.info("Starting European scam database update job...")
            
            # Get the directory of the current script
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(script_dir, 'update_scam_db_eu.py')
            
            # Run the update script
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                cwd=script_dir
            )
            
            if result.returncode == 0:
                logger.info("European scam database update completed successfully")
                logger.info(f"Update output: {result.stdout}")
            else:
                logger.error(f"European scam database update failed with return code {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                
        except Exception as e:
            logger.error(f"European scam database update job failed: {str(e)}", exc_info=True)
    
    def generate_blog_post_job(self):
        """Daily SEO blog post generation job"""
        try:
            logger.info("Starting daily blog post generation job...")
            from services.blog_generator import generate_daily_blog_post
            if self._app:
                result = generate_daily_blog_post(self._app)
                if result:
                    logger.info("Daily blog post generated successfully")
                else:
                    logger.info("Blog post generation skipped (already exists today or no content)")
            else:
                logger.warning("Blog generation skipped: no Flask app reference in scheduler")
        except Exception as e:
            logger.error(f"Daily blog post generation job failed: {str(e)}", exc_info=True)

    def shutdown(self):
        """Shutdown scheduler"""
        self.scheduler.shutdown()
        logger.info("MonitoringScheduler shut down")
    
    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()

# Global scheduler instance
scheduler = None

def init_scheduler(app=None):
    """Initialize scheduler"""
    global scheduler
    scheduler = MonitoringScheduler(app=app)
    scheduler.setup_jobs()
    return scheduler

def get_scheduler():
    """Get scheduler instance"""
    return scheduler
