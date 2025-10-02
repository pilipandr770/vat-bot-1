import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List
import logging
from flask import current_app
from flask_mail import Message

logger = logging.getLogger(__name__)

# Helper function for Flask-Mail
def send_email(subject, recipient, text_body, html_body=None):
    """Send email using Flask-Mail."""
    try:
        from app import mail
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=text_body,
            html=html_body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        logger.info(f'Email sent to {recipient}: {subject}')
        return True
    except Exception as e:
        logger.error(f'Error sending email: {str(e)}')
        return False

class NotificationService:
    """Service for sending notifications via Email and Telegram."""
    
    def __init__(self, config):
        self.config = config
        self.smtp_server = config.get('SMTP_SERVER')
        self.smtp_port = config.get('SMTP_PORT', 587)
        self.smtp_username = config.get('SMTP_USERNAME')
        self.smtp_password = config.get('SMTP_PASSWORD')
        
        self.telegram_token = config.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = config.get('TELEGRAM_CHAT_ID')
    
    def send_alert(self, alert_data: Dict, channels: List[str] = None) -> Dict:
        """
        Send alert via specified channels.
        
        Args:
            alert_data: Alert information
            channels: List of channels ('email', 'telegram'). If None, use both.
        
        Returns:
            Status of notification sending
        """
        if channels is None:
            channels = ['email', 'telegram']
        
        results = {
            'sent_at': datetime.utcnow().isoformat(),
            'channels': {},
            'success': True
        }
        
        # Send via email
        if 'email' in channels and self._is_email_configured():
            email_result = self._send_email_alert(alert_data)
            results['channels']['email'] = email_result
            if not email_result['success']:
                results['success'] = False
        
        # Send via Telegram
        if 'telegram' in channels and self._is_telegram_configured():
            telegram_result = self._send_telegram_alert(alert_data)
            results['channels']['telegram'] = telegram_result
            if not telegram_result['success']:
                results['success'] = False
        
        return results
    
    def send_daily_summary(self, monitoring_summary: Dict) -> Dict:
        """Send daily monitoring summary."""
        
        # Prepare summary message
        message_data = {
            'type': 'daily_summary',
            'title': 'Daily Monitoring Summary',
            'summary': monitoring_summary,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Only send if there are changes or errors
        if (monitoring_summary.get('changes_detected', 0) > 0 or 
            monitoring_summary.get('alerts_created', 0) > 0 or 
            len(monitoring_summary.get('errors', [])) > 0):
            
            return self.send_alert(message_data, ['email', 'telegram'])
        
        return {
            'sent_at': datetime.utcnow().isoformat(),
            'skipped': True,
            'reason': 'No changes or alerts to report'
        }
    
    def _send_email_alert(self, alert_data: Dict) -> Dict:
        """Send alert via email."""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.smtp_username  # For now, send to self
            msg['Subject'] = self._get_email_subject(alert_data)
            
            # Create email body
            body = self._format_email_body(alert_data)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return {
                'success': True,
                'channel': 'email',
                'recipient': self.smtp_username,
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return {
                'success': False,
                'channel': 'email',
                'error': str(e),
                'attempted_at': datetime.utcnow().isoformat()
            }
    
    def _send_telegram_alert(self, alert_data: Dict) -> Dict:
        """Send alert via Telegram."""
        try:
            # Format message for Telegram
            message = self._format_telegram_message(alert_data)
            
            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            return {
                'success': True,
                'channel': 'telegram',
                'chat_id': self.telegram_chat_id,
                'sent_at': datetime.utcnow().isoformat(),
                'message_id': response.json().get('result', {}).get('message_id')
            }
            
        except Exception as e:
            logger.error(f"Telegram sending failed: {str(e)}")
            return {
                'success': False,
                'channel': 'telegram',
                'error': str(e),
                'attempted_at': datetime.utcnow().isoformat()
            }
    
    def _get_email_subject(self, alert_data: Dict) -> str:
        """Generate email subject based on alert data."""
        alert_type = alert_data.get('type', 'alert')
        
        if alert_type == 'daily_summary':
            changes = alert_data.get('summary', {}).get('changes_detected', 0)
            alerts = alert_data.get('summary', {}).get('alerts_created', 0)
            return f"Daily Monitoring Summary - {changes} changes, {alerts} alerts"
        
        elif alert_type == 'sanctions_found':
            return "🚨 CRITICAL: Sanctions Match Detected"
        
        elif alert_type == 'status_change':
            return f"⚠️ Status Change Alert - {alert_data.get('service', 'Unknown')}"
        
        else:
            return f"Counterparty Alert - {alert_type}"
    
    def _format_email_body(self, alert_data: Dict) -> str:
        """Format HTML email body."""
        alert_type = alert_data.get('type', 'alert')
        
        if alert_type == 'daily_summary':
            return self._format_daily_summary_email(alert_data.get('summary', {}))
        
        # Standard alert email template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; }}
                .alert-critical {{ background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; }}
                .alert-high {{ background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; }}
                .alert-medium {{ background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; }}
                .details {{ margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding: 15px; background-color: #f9f9f9; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Counterparty Verification Alert</h2>
                    <p><strong>Time:</strong> {alert_data.get('timestamp', 'Unknown')}</p>
                </div>
                
                <div class="alert-{alert_data.get('severity', 'medium')}">
                    <h3>{alert_data.get('title', 'Alert')}</h3>
                    <p>{alert_data.get('message', 'No message provided')}</p>
                </div>
                
                <div class="details">
                    {self._format_alert_details_html(alert_data)}
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from the Counterparty Verification System.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_daily_summary_email(self, summary: Dict) -> str:
        """Format daily summary email."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .summary-stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ text-align: center; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }}
                .stat-number {{ font-size: 24px; font-weight: bold; color: #2196f3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Daily Monitoring Summary</h2>
                <p><strong>Report Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d')}</p>
                
                <div class="summary-stats">
                    <div class="stat-box">
                        <div class="stat-number">{summary.get('total_checks_monitored', 0)}</div>
                        <div>Checks Monitored</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{summary.get('changes_detected', 0)}</div>
                        <div>Changes Detected</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{summary.get('alerts_created', 0)}</div>
                        <div>Alerts Created</div>
                    </div>
                </div>
                
                {self._format_summary_details_html(summary)}
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_telegram_message(self, alert_data: Dict) -> str:
        """Format message for Telegram."""
        alert_type = alert_data.get('type', 'alert')
        
        if alert_type == 'daily_summary':
            summary = alert_data.get('summary', {})
            message = f"""
🔍 <b>Daily Monitoring Summary</b>

📊 <b>Statistics:</b>
• Checks monitored: {summary.get('total_checks_monitored', 0)}
• Changes detected: {summary.get('changes_detected', 0)}
• Alerts created: {summary.get('alerts_created', 0)}

⏰ <i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</i>
            """
            
            if summary.get('errors'):
                message += f"\n❌ <b>Errors:</b> {len(summary['errors'])}"
            
            return message.strip()
        
        # Standard alert message
        emoji_map = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': 'ℹ️',
            'low': '📝'
        }
        
        severity = alert_data.get('severity', 'medium')
        emoji = emoji_map.get(severity, 'ℹ️')
        
        message = f"""
{emoji} <b>Alert: {alert_data.get('title', 'Counterparty Alert')}</b>

{alert_data.get('message', 'No message provided')}

<b>Severity:</b> {severity.upper()}
<b>Time:</b> {alert_data.get('timestamp', 'Unknown')}
        """
        
        return message.strip()
    
    def _format_alert_details_html(self, alert_data: Dict) -> str:
        """Format alert details for HTML email."""
        details = alert_data.get('details', {})
        if not details:
            return "<p>No additional details available.</p>"
        
        html = "<h4>Details:</h4><ul>"
        for key, value in details.items():
            html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        html += "</ul>"
        
        return html
    
    def _format_summary_details_html(self, summary: Dict) -> str:
        """Format summary details for HTML email."""
        html = ""
        
        if summary.get('errors'):
            html += "<h4>Errors:</h4><ul>"
            for error in summary['errors']:
                html += f"<li>{error}</li>"
            html += "</ul>"
        
        return html
    
    def _is_email_configured(self) -> bool:
        """Check if email configuration is available."""
        return all([
            self.smtp_server,
            self.smtp_username,
            self.smtp_password
        ])
    
    def _is_telegram_configured(self) -> bool:
        """Check if Telegram configuration is available."""
        return all([
            self.telegram_token,
            self.telegram_chat_id
        ])
    
    def test_notifications(self) -> Dict:
        """Test all configured notification channels."""
        results = {
            'tested_at': datetime.utcnow().isoformat(),
            'channels': {}
        }
        
        test_alert = {
            'type': 'test',
            'title': 'Test Notification',
            'message': 'This is a test notification from the Counterparty Verification System.',
            'severity': 'low',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self._is_email_configured():
            results['channels']['email'] = self._send_email_alert(test_alert)
        
        if self._is_telegram_configured():
            results['channels']['telegram'] = self._send_telegram_alert(test_alert)
        
        results['success'] = all(
            result.get('success', False) 
            for result in results['channels'].values()
        )
        
        return results