"""
Monitoring Service - Daily Counterparty Verification & Change Detection
"""
from crm.models import db, Counterparty, VerificationCheck, CheckResult, Alert
from services.vies import VIESService
from services.handelsregister import HandelsregisterService
from services.sanctions import SanctionsService
# from services.insolvenz import InsolvenzService  # TODO: Create insolvency service
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class MonitoringService:
    """Service for monitoring counterparty status changes"""
    
    def __init__(self):
        self.vies_service = VIESService()
        self.handelsregister_service = HandelsregisterService()
        self.sanctions_service = SanctionsService()
        # self.insolvenz_service = InsolvenzService()  # TODO: Implement
    
    def run_daily_checks(self):
        """
        Run verification checks for all monitored counterparties.
        Detects changes and creates alerts.
        """
        logger.info("Starting daily monitoring checks...")
        
        # Get all active monitoring checks
        active_checks = VerificationCheck.query.filter_by(is_monitoring_active=True).all()
        
        logger.info(f"Found {len(active_checks)} active monitoring checks")
        
        for check in active_checks:
            try:
                self.check_counterparty(check)
            except Exception as e:
                logger.error(f"Error checking counterparty {check.counterparty_id}: {str(e)}")
                continue
        
        logger.info("Daily monitoring checks completed")
    
    def check_counterparty(self, verification_check: VerificationCheck):
        """
        Run verification for single counterparty and detect changes.
        """
        counterparty = verification_check.counterparty
        logger.info(f"Checking counterparty: {counterparty.company_name} ({counterparty.vat_number})")
        
        # Get previous results for comparison
        previous_results = self._get_latest_results(verification_check.id)
        
        # Run new verifications
        new_results = {}
        changes_detected = []
        
        # 1. VIES Check
        if counterparty.vat_number and counterparty.country:
            try:
                vies_result = self.vies_service.validate_vat(
                    counterparty.country, 
                    counterparty.vat_number.replace(counterparty.country, '')
                )
                new_results['vies'] = vies_result
                
                # Compare with previous
                if 'vies' in previous_results:
                    vies_changes = self._detect_vies_changes(previous_results['vies'], vies_result)
                    if vies_changes:
                        changes_detected.extend(vies_changes)
            except Exception as e:
                logger.error(f"VIES check failed: {str(e)}")
        
        # 2. Sanctions Check
        try:
            sanctions_result = self.sanctions_service.check_sanctions(
                counterparty.company_name,
                counterparty.country
            )
            new_results['sanctions'] = sanctions_result
            
            # Compare with previous
            if 'sanctions' in previous_results:
                sanctions_changes = self._detect_sanctions_changes(previous_results['sanctions'], sanctions_result)
                if sanctions_changes:
                    changes_detected.extend(sanctions_changes)
        except Exception as e:
            logger.error(f"Sanctions check failed: {str(e)}")
        
        # 3. Handelsregister Check (Germany only)
        if counterparty.country == 'DE' and counterparty.company_name:
            try:
                hr_result = self.handelsregister_service.search_company(counterparty.company_name)
                new_results['handelsregister'] = hr_result
                
                # Compare with previous
                if 'handelsregister' in previous_results:
                    hr_changes = self._detect_company_data_changes(previous_results['handelsregister'], hr_result)
                    if hr_changes:
                        changes_detected.extend(hr_changes)
            except Exception as e:
                logger.error(f"Handelsregister check failed: {str(e)}")
        
        # 4. Insolvency Check (Germany only) - TODO: Implement insolvency service
        # if counterparty.country == 'DE' and counterparty.company_name:
        #     try:
        #         insolvenz_result = self.insolvenz_service.check_insolvency(counterparty.company_name)
        #         new_results['insolvenz'] = insolvenz_result
        #         
        #         # Compare with previous
        #         if 'insolvenz' in previous_results:
        #             insolvenz_changes = self._detect_insolvency_changes(previous_results['insolvenz'], insolvenz_result)
        #             if insolvenz_changes:
        #                 changes_detected.extend(insolvenz_changes)
        #     except Exception as e:
        #         logger.error(f"Insolvency check failed: {str(e)}")
        
        # Save new check results
        for service_name, result in new_results.items():
            check_result = CheckResult(
                check_id=verification_check.id,
                service_name=service_name,
                status=result.get('status', 'error'),
                confidence_score=result.get('confidence', 0.0),
                data_json=json.dumps(result.get('data', {})),
                error_message=result.get('error'),
                created_at=datetime.utcnow()
            )
            db.session.add(check_result)
        
        # Update verification check
        verification_check.check_date = datetime.utcnow()
        verification_check.overall_status = self._calculate_overall_status(new_results)
        
        # Create alerts for changes
        if changes_detected:
            for change in changes_detected:
                alert = Alert(
                    check_id=verification_check.id,
                    alert_type=change['type'],
                    message=change['message'],
                    severity=change['severity'],
                    is_sent=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(alert)
            
            logger.info(f"Created {len(changes_detected)} alerts for counterparty {counterparty.id}")
        
        db.session.commit()
    
    def _get_latest_results(self, check_id: int) -> dict:
        """Get latest check results for each service"""
        results = {}
        
        check_results = CheckResult.query.filter_by(check_id=check_id)\
            .order_by(CheckResult.created_at.desc()).all()
        
        for result in check_results:
            if result.service_name not in results:
                results[result.service_name] = result.data
        
        return results
    
    def _detect_vies_changes(self, old_data: dict, new_data: dict) -> list:
        """Detect changes in VIES validation"""
        changes = []
        
        old_valid = old_data.get('data', {}).get('valid', False)
        new_valid = new_data.get('data', {}).get('valid', False)
        
        if old_valid and not new_valid:
            changes.append({
                'type': 'vat_invalid',
                'message': f'VAT number became INVALID. Previous: valid, Current: invalid',
                'severity': 'critical'
            })
        elif not old_valid and new_valid:
            changes.append({
                'type': 'vat_valid',
                'message': f'VAT number became VALID. Previous: invalid, Current: valid',
                'severity': 'low'
            })
        
        # Check company name changes
        old_name = old_data.get('data', {}).get('name', '')
        new_name = new_data.get('data', {}).get('name', '')
        
        if old_name and new_name and old_name != new_name:
            changes.append({
                'type': 'company_name_changed',
                'message': f'Company name changed. Previous: "{old_name}", Current: "{new_name}"',
                'severity': 'medium'
            })
        
        # Check address changes
        old_address = old_data.get('data', {}).get('address', '')
        new_address = new_data.get('data', {}).get('address', '')
        
        if old_address and new_address and old_address != new_address:
            changes.append({
                'type': 'address_changed',
                'message': f'Address changed. Previous: "{old_address}", Current: "{new_address}"',
                'severity': 'medium'
            })
        
        return changes
    
    def _detect_sanctions_changes(self, old_data: dict, new_data: dict) -> list:
        """Detect changes in sanctions status"""
        changes = []
        
        old_sanctioned = old_data.get('data', {}).get('is_sanctioned', False)
        new_sanctioned = new_data.get('data', {}).get('is_sanctioned', False)
        
        if not old_sanctioned and new_sanctioned:
            changes.append({
                'type': 'sanctions_found',
                'message': f'SANCTIONS DETECTED! Company appeared on sanctions lists.',
                'severity': 'critical'
            })
        elif old_sanctioned and not new_sanctioned:
            changes.append({
                'type': 'sanctions_removed',
                'message': f'Sanctions removed. Company no longer on sanctions lists.',
                'severity': 'low'
            })
        
        return changes
    
    def _detect_insolvency_changes(self, old_data: dict, new_data: dict) -> list:
        """Detect changes in insolvency status"""
        changes = []
        
        old_insolvent = old_data.get('data', {}).get('has_insolvency', False)
        new_insolvent = new_data.get('data', {}).get('has_insolvency', False)
        
        if not old_insolvent and new_insolvent:
            changes.append({
                'type': 'insolvency_started',
                'message': f'INSOLVENCY DETECTED! Insolvency proceedings started.',
                'severity': 'critical'
            })
        
        return changes
    
    def _detect_company_data_changes(self, old_data: dict, new_data: dict) -> list:
        """Detect changes in company registry data"""
        changes = []
        
        # Check registered address
        old_address = old_data.get('data', {}).get('address', '')
        new_address = new_data.get('data', {}).get('address', '')
        
        if old_address and new_address and old_address != new_address:
            changes.append({
                'type': 'registry_address_changed',
                'message': f'Registered address changed in Handelsregister',
                'severity': 'medium'
            })
        
        # Check legal form
        old_form = old_data.get('data', {}).get('legal_form', '')
        new_form = new_data.get('data', {}).get('legal_form', '')
        
        if old_form and new_form and old_form != new_form:
            changes.append({
                'type': 'legal_form_changed',
                'message': f'Legal form changed. Previous: "{old_form}", Current: "{new_form}"',
                'severity': 'high'
            })
        
        return changes
    
    def _calculate_overall_status(self, results: dict) -> str:
        """Calculate overall status from all service results"""
        statuses = [r.get('status', 'error') for r in results.values()]
        
        if 'error' in statuses:
            return 'error'
        elif 'warning' in statuses:
            return 'warning'
        else:
            return 'valid'

# Global monitoring service instance
monitoring_service = MonitoringService()
