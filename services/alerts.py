"""
Alert Notification Service - Email alerts for monitoring changes
"""
from flask import render_template_string, url_for
from flask_mail import Message, Mail
from crm.models import db, Alert, VerificationCheck
from auth.models import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlertService:
    """Service for sending alert notifications"""
    
    def __init__(self, mail: Mail):
        self.mail = mail
    
    def send_pending_alerts(self):
        """Send all pending alerts via email"""
        pending_alerts = Alert.query.filter_by(is_sent=False).all()
        
        logger.info(f"Found {len(pending_alerts)} pending alerts to send")
        
        # Group alerts by user
        alerts_by_user = {}
        for alert in pending_alerts:
            user_id = alert.verification_check.user_id
            if user_id not in alerts_by_user:
                alerts_by_user[user_id] = []
            alerts_by_user[user_id].append(alert)
        
        # Send emails
        for user_id, user_alerts in alerts_by_user.items():
            try:
                self.send_user_alert_email(user_id, user_alerts)
                
                # Mark alerts as sent
                for alert in user_alerts:
                    alert.is_sent = True
                    alert.sent_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Failed to send alerts to user {user_id}: {str(e)}")
                continue
        
        db.session.commit()
        logger.info(f"Sent {len(pending_alerts)} alerts")
    
    def send_user_alert_email(self, user_id: int, alerts: list):
        """Send alert email to specific user"""
        user = User.query.get(user_id)
        if not user or not user.email:
            logger.warning(f"User {user_id} not found or no email")
            return
        
        # Group alerts by severity
        critical_alerts = [a for a in alerts if a.severity == 'critical']
        high_alerts = [a for a in alerts if a.severity == 'high']
        medium_alerts = [a for a in alerts if a.severity == 'medium']
        low_alerts = [a for a in alerts if a.severity == 'low']
        
        # Prepare email content
        subject = f"🚨 Counterparty Monitoring Alerts ({len(alerts)} changes detected)"
        
        html_body = self._generate_alert_email_html(
            user=user,
            critical=critical_alerts,
            high=high_alerts,
            medium=medium_alerts,
            low=low_alerts
        )
        
        # Send email
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=html_body
        )
        
        self.mail.send(msg)
        logger.info(f"Alert email sent to {user.email}")
    
    def _generate_alert_email_html(self, user, critical, high, medium, low):
        """Generate HTML email content for alerts"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         color: white; padding: 20px; border-radius: 8px; }
                .alert-section { margin: 20px 0; }
                .alert-card { background: #f8f9fa; border-left: 4px solid #666; 
                             padding: 15px; margin: 10px 0; border-radius: 4px; }
                .alert-critical { border-left-color: #dc3545; background: #ffe5e8; }
                .alert-high { border-left-color: #fd7e14; background: #fff3e0; }
                .alert-medium { border-left-color: #ffc107; background: #fffbf0; }
                .alert-low { border-left-color: #28a745; background: #e8f5e9; }
                .alert-title { font-weight: bold; margin-bottom: 8px; }
                .counterparty-name { color: #667eea; font-weight: bold; }
                .btn { display: inline-block; padding: 12px 24px; background: #667eea; 
                      color: white; text-decoration: none; border-radius: 6px; margin-top: 20px; }
                .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; 
                         color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Counterparty Monitoring Alerts</h1>
                    <p>Hallo {{ user.first_name or user.email }},</p>
                    <p>Wir haben Änderungen bei Ihren überwachten Kontrahenten festgestellt.</p>
                </div>
                
                {% if critical %}
                <div class="alert-section">
                    <h2 style="color: #dc3545;">🔴 Kritische Alerts ({{ critical|length }})</h2>
                    {% for alert in critical %}
                    <div class="alert-card alert-critical">
                        <div class="alert-title">
                            <span class="counterparty-name">{{ alert.verification_check.counterparty.company_name }}</span>
                            <span style="color: #666; font-size: 12px;">
                                ({{ alert.verification_check.counterparty.vat_number }})
                            </span>
                        </div>
                        <div>{{ alert.message }}</div>
                        <div style="font-size: 12px; color: #666; margin-top: 8px;">
                            {{ alert.created_at.strftime('%d.%m.%Y %H:%M') }} Uhr
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if high %}
                <div class="alert-section">
                    <h2 style="color: #fd7e14;">🟠 Hohe Priorität ({{ high|length }})</h2>
                    {% for alert in high %}
                    <div class="alert-card alert-high">
                        <div class="alert-title">
                            <span class="counterparty-name">{{ alert.verification_check.counterparty.company_name }}</span>
                        </div>
                        <div>{{ alert.message }}</div>
                        <div style="font-size: 12px; color: #666; margin-top: 8px;">
                            {{ alert.created_at.strftime('%d.%m.%Y %H:%M') }} Uhr
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if medium %}
                <div class="alert-section">
                    <h2 style="color: #ffc107;">🟡 Mittlere Priorität ({{ medium|length }})</h2>
                    {% for alert in medium %}
                    <div class="alert-card alert-medium">
                        <div class="alert-title">
                            <span class="counterparty-name">{{ alert.verification_check.counterparty.company_name }}</span>
                        </div>
                        <div>{{ alert.message }}</div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if low %}
                <div class="alert-section">
                    <h2 style="color: #28a745;">🟢 Niedrige Priorität ({{ low|length }})</h2>
                    {% for alert in low %}
                    <div class="alert-card alert-low">
                        <div class="alert-title">
                            <span class="counterparty-name">{{ alert.verification_check.counterparty.company_name }}</span>
                        </div>
                        <div>{{ alert.message }}</div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                <div style="text-align: center;">
                    <a href="{{ url_for('crm.index', _external=True) }}" class="btn">
                        📊 CRM Dashboard öffnen
                    </a>
                </div>
                
                <div class="footer">
                    <p><strong>Was Sie jetzt tun sollten:</strong></p>
                    <ul>
                        <li>Überprüfen Sie die kritischen Alerts sofort</li>
                        <li>Kontaktieren Sie betroffene Kontrahenten bei Bedarf</li>
                        <li>Aktualisieren Sie Ihre Unterlagen</li>
                        <li>Deaktivieren Sie Monitoring für inaktive Kontrahenten</li>
                    </ul>
                    
                    <p style="margin-top: 20px;">
                        Diese E-Mail wurde automatisch generiert von Ihrem VAT Verification System.<br>
                        Sie erhalten diese Benachrichtigungen, weil Sie Counterparty Monitoring aktiviert haben.
                    </p>
                    
                    <p>
                        <a href="{{ url_for('crm.index', _external=True) }}" style="color: #667eea;">CRM Dashboard</a> | 
                        <a href="{{ url_for('dashboard', _external=True) }}" style="color: #667eea;">Dashboard</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(
            template,
            user=user,
            critical=critical,
            high=high,
            medium=medium,
            low=low
        )

# Global alert service (will be initialized in app factory with mail instance)
alert_service = None

def init_alert_service(mail):
    """Initialize alert service with mail instance"""
    global alert_service
    alert_service = AlertService(mail)
    return alert_service
