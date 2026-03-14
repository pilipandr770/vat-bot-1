"""
CRM Monitoring Scheduler
Automated daily checks for counterparty status changes
"""
from apscheduler.schedulers.background import BackgroundScheduler
from crm.monitor import MonitoringService
import logging

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Manages scheduled monitoring tasks"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def setup(self, app):
        """
        Setup scheduler with Flask app context.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Job: Daily monitoring at 02:00 UTC
        self.scheduler.add_job(
            func=self._run_daily_monitoring,
            trigger='cron',
            hour=2,
            minute=0,
            id='daily_monitoring',
            name='Daily Counterparty Monitoring',
            replace_existing=True,
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        logger.info("✅ Monitoring scheduler configured")
        logger.info("   - Daily monitoring: 02:00 UTC")
        
        return self
    
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("🚀 Monitoring scheduler started")
        else:
            logger.warning("Scheduler already running")
    
    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("⏹️  Monitoring scheduler stopped")
    
    def _run_daily_monitoring(self):
        """Execute daily monitoring within Flask app context"""
        with self.app.app_context():
            try:
                logger.info("=== STARTING DAILY MONITORING JOB ===")
                
                monitoring_service = MonitoringService()
                result = monitoring_service.run_daily_monitoring(days_back=30)
                
                logger.info("=== DAILY MONITORING COMPLETED ===")
                logger.info(f"  Total checks monitored: {result.get('total_checks_monitored', 0)}")
                logger.info(f"  Changes detected: {result.get('changes_detected', 0)}")
                logger.info(f"  Alerts created: {result.get('alerts_created', 0)}")
                logger.info(f"  Duration: {result.get('duration_seconds', 0):.2f}s")
                
                if result.get('errors'):
                    logger.error(f"  Errors: {len(result['errors'])}")
                    for error in result['errors'][:5]:  # Show first 5 errors
                        logger.error(f"    - {error}")
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Daily monitoring job failed: {str(e)}", exc_info=True)
                return {'error': str(e)}
    
    def run_manual_monitoring(self, days_back=30):
        """
        Run monitoring manually (for testing or on-demand).
        Must be called within Flask app context.
        
        Args:
            days_back: Number of days to look back
        
        Returns:
            Monitoring results dictionary
        """
        logger.info(f"Running manual monitoring (days_back={days_back})")
        monitoring_service = MonitoringService()
        return monitoring_service.run_daily_monitoring(days_back=days_back)


# Global scheduler instance
monitoring_scheduler = MonitoringScheduler()


def init_monitoring_scheduler(app):
    """
    Initialize and start monitoring scheduler.
    Call this from application.py after app creation.
    
    Args:
        app: Flask application instance
    
    Returns:
        MonitoringScheduler instance
    """
    monitoring_scheduler.setup(app)
    monitoring_scheduler.start()
    
    logger.info("📅 Monitoring scheduler initialized")
    
    # Register shutdown handler
    import atexit
    atexit.register(lambda: monitoring_scheduler.stop())
    
    return monitoring_scheduler
