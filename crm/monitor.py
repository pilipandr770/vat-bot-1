from datetime import datetime, timedelta
from typing import List, Dict
from crm.models import db, VerificationCheck, CheckResult, Alert
from services.vies import VIESService
from services.sanctions import SanctionsService
from services.handelsregister import HandelsregisterService
from crm.save_results import ResultsSaver
import logging

logger = logging.getLogger(__name__)

class MonitoringService:
    """Service for daily monitoring and change detection."""
    
    def __init__(self):
        self.vies_service = VIESService()
        self.sanctions_service = SanctionsService()
        self.handelsregister_service = HandelsregisterService()
        self.results_saver = ResultsSaver(db)
    
    def run_daily_monitoring(self, days_back: int = 1) -> Dict:
        """
        Run daily monitoring for active verification checks.
        
        Args:
            days_back: Number of days to look back for active checks
        
        Returns:
            Summary of monitoring results
        """
        start_time = datetime.utcnow()
        logger.info("Starting daily monitoring...")
        
        try:
            # Find active checks from recent days
            cutoff_date = datetime.utcnow() - timedelta(days=days_back * 30)  # Monitor checks from last N months
            
            active_checks = VerificationCheck.query.filter(
                VerificationCheck.is_monitoring_active == True,
                VerificationCheck.check_date >= cutoff_date
            ).all()
            
            monitoring_summary = {
                'started_at': start_time.isoformat(),
                'total_checks_monitored': len(active_checks),
                'changes_detected': 0,
                'alerts_created': 0,
                'errors': [],
                'check_details': []
            }
            
            for check in active_checks:
                try:
                    check_result = self._monitor_single_check(check)
                    monitoring_summary['check_details'].append(check_result)
                    
                    if check_result.get('changes_detected', 0) > 0:
                        monitoring_summary['changes_detected'] += 1
                    
                    monitoring_summary['alerts_created'] += check_result.get('alerts_created', 0)
                    
                except Exception as e:
                    error_msg = f"Error monitoring check {check.id}: {str(e)}"
                    monitoring_summary['errors'].append(error_msg)
                    logger.error(error_msg)
            
            monitoring_summary['completed_at'] = datetime.utcnow().isoformat()
            monitoring_summary['duration_seconds'] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Daily monitoring completed. {monitoring_summary['changes_detected']} changes detected, "
                       f"{monitoring_summary['alerts_created']} alerts created")
            
            return monitoring_summary
            
        except Exception as e:
            logger.error(f"Daily monitoring failed: {str(e)}")
            return {
                'started_at': start_time.isoformat(),
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }
    
    def _monitor_single_check(self, check: VerificationCheck) -> Dict:
        """Monitor a single verification check for changes."""
        check_start_time = datetime.utcnow()
        
        # Get latest results for comparison
        latest_results = check.get_latest_results()
        
        # Re-run verification services
        counterparty = check.counterparty
        new_verification_results = self._run_verification_services(counterparty)
        
        # Compare results and detect changes
        changes = self._detect_changes(latest_results, new_verification_results)
        
        # Save new results if there are changes
        alerts_created = 0
        if changes['has_changes']:
            # Create new verification check for monitoring
            monitoring_check = VerificationCheck(
                company_id=check.company_id,
                counterparty_id=check.counterparty_id,
                overall_status='pending'
            )
            db.session.add(monitoring_check)
            db.session.commit()
            
            # Save new results
            overall_status, confidence = self.results_saver.save_verification_results(
                monitoring_check.id, new_verification_results
            )
            
            # Update status
            monitoring_check.overall_status = overall_status
            monitoring_check.confidence_score = confidence
            db.session.commit()
            
            # Create alerts for significant changes
            alerts_created = self._create_alerts_for_changes(check.id, changes)
        
        return {
            'check_id': check.id,
            'counterparty_name': counterparty.company_name,
            'counterparty_country': counterparty.country,
            'monitored_at': check_start_time.isoformat(),
            'changes_detected': len(changes['changes']),
            'has_changes': changes['has_changes'],
            'alerts_created': alerts_created,
            'change_details': changes['changes']
        }
    
    def _run_verification_services(self, counterparty) -> Dict:
        """Re-run verification services for a counterparty."""
        results = {}
        
        try:
            # VIES VAT validation
            if counterparty.vat_number:
                vies_result = self.vies_service.validate_vat(
                    counterparty.country,
                    counterparty.vat_number
                )
                results['vies'] = vies_result
        except Exception as e:
            logger.error(f"VIES check failed for {counterparty.company_name}: {str(e)}")
        
        try:
            # Handelsregister (for German companies)
            if counterparty.country.upper() == 'DE':
                handelsregister_result = self.handelsregister_service.check_company(
                    counterparty.company_name
                )
                results['handelsregister'] = handelsregister_result
        except Exception as e:
            logger.error(f"Handelsregister check failed for {counterparty.company_name}: {str(e)}")
        
        try:
            # Sanctions check
            sanctions_result = self.sanctions_service.check_sanctions(
                counterparty.company_name,
                counterparty.contact_person or ''
            )
            results['sanctions'] = sanctions_result
        except Exception as e:
            logger.error(f"Sanctions check failed for {counterparty.company_name}: {str(e)}")
        
        return results
    
    def _detect_changes(self, old_results: Dict, new_results: Dict) -> Dict:
        """Detect changes between old and new verification results."""
        changes = []
        has_significant_changes = False
        
        for service_name, new_result in new_results.items():
            if service_name in old_results:
                old_result = old_results[service_name]
                service_changes = self._compare_service_results(service_name, old_result, new_result)
                
                if service_changes:
                    changes.extend(service_changes)
                    
                    # Check if this is a significant change
                    for change in service_changes:
                        if change['severity'] in ['high', 'critical']:
                            has_significant_changes = True
            else:
                # New service result
                changes.append({
                    'service': service_name,
                    'type': 'new_service',
                    'severity': 'medium',
                    'description': f'New service {service_name} result available',
                    'new_status': new_result.get('status'),
                    'new_confidence': new_result.get('confidence')
                })
        
        return {
            'has_changes': len(changes) > 0,
            'has_significant_changes': has_significant_changes,
            'changes': changes,
            'total_changes': len(changes)
        }
    
    def _compare_service_results(self, service_name: str, old_result: CheckResult, new_result: Dict) -> List[Dict]:
        """Compare results from a single service."""
        changes = []
        
        old_status = old_result.status
        new_status = new_result.get('status')
        old_confidence = old_result.confidence_score
        new_confidence = new_result.get('confidence', 0)
        
        # Status changes
        if old_status != new_status:
            severity = self._get_status_change_severity(old_status, new_status, service_name)
            changes.append({
                'service': service_name,
                'type': 'status_change',
                'severity': severity,
                'description': f'{service_name} status changed from {old_status} to {new_status}',
                'old_status': old_status,
                'new_status': new_status,
                'old_confidence': old_confidence,
                'new_confidence': new_confidence
            })
        
        # Significant confidence changes
        confidence_change = abs(new_confidence - old_confidence)
        if confidence_change > 0.2:  # 20% threshold
            severity = 'high' if confidence_change > 0.5 else 'medium'
            changes.append({
                'service': service_name,
                'type': 'confidence_change',
                'severity': severity,
                'description': f'{service_name} confidence changed by {confidence_change:.2f}',
                'old_confidence': old_confidence,
                'new_confidence': new_confidence,
                'change_amount': confidence_change
            })
        
        # Service-specific data changes
        if service_name == 'sanctions':
            sanctions_changes = self._detect_sanctions_changes(old_result, new_result)
            changes.extend(sanctions_changes)
        
        return changes
    
    def _get_status_change_severity(self, old_status: str, new_status: str, service_name: str) -> str:
        """Determine severity of status changes."""
        # Critical: Any change to error status in sanctions
        if service_name == 'sanctions' and new_status == 'error':
            return 'critical'
        
        # High: Valid to error, or error to valid
        if (old_status == 'valid' and new_status == 'error') or (old_status == 'error' and new_status == 'valid'):
            return 'high'
        
        # Medium: Other status changes
        return 'medium'
    
    def _detect_sanctions_changes(self, old_result: CheckResult, new_result: Dict) -> List[Dict]:
        """Detect specific changes in sanctions results."""
        changes = []
        
        try:
            old_data = old_result.data or {}
            new_data = new_result.get('data', {})
            
            old_matches = len(old_data.get('sanctions_found', []))
            new_matches = len(new_data.get('sanctions_found', []))
            
            if new_matches > old_matches:
                changes.append({
                    'service': 'sanctions',
                    'type': 'new_sanctions_found',
                    'severity': 'critical',
                    'description': f'New sanctions matches found: {new_matches - old_matches}',
                    'old_matches': old_matches,
                    'new_matches': new_matches,
                    'new_sanctions': new_data.get('sanctions_found', [])
                })
            elif old_matches > new_matches:
                changes.append({
                    'service': 'sanctions',
                    'type': 'sanctions_removed',
                    'severity': 'high',
                    'description': f'Sanctions matches removed: {old_matches - new_matches}',
                    'old_matches': old_matches,
                    'new_matches': new_matches
                })
        
        except Exception as e:
            logger.error(f"Error detecting sanctions changes: {str(e)}")
        
        return changes
    
    def _create_alerts_for_changes(self, original_check_id: int, changes: Dict) -> int:
        """Create alerts for detected changes."""
        alerts_created = 0
        
        try:
            for change in changes['changes']:
                if change['severity'] in ['high', 'critical']:
                    alert = Alert(
                        check_id=original_check_id,
                        alert_type=change['type'],
                        message=change['description'],
                        severity=change['severity']
                    )
                    db.session.add(alert)
                    alerts_created += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating alerts: {str(e)}")
        
        return alerts_created
    
    def get_monitoring_statistics(self, days: int = 30) -> Dict:
        """Get monitoring statistics for the last N days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count alerts by severity
            from sqlalchemy import func
            
            alerts_stats = db.session.query(
                Alert.severity,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at >= cutoff_date
            ).group_by(Alert.severity).all()
            
            # Get recent monitoring activity
            recent_checks = VerificationCheck.query.filter(
                VerificationCheck.check_date >= cutoff_date,
                VerificationCheck.is_monitoring_active == True
            ).count()
            
            return {
                'period_days': days,
                'total_monitored_checks': recent_checks,
                'alerts_by_severity': {stat.severity: stat.count for stat in alerts_stats},
                'total_alerts': sum(stat.count for stat in alerts_stats),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f"Error getting monitoring statistics: {str(e)}",
                'generated_at': datetime.utcnow().isoformat()
            }