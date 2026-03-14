from typing import Dict, Tuple
from datetime import datetime
import json
from crm.models import db, CheckResult

class ResultsSaver:
    """Service for saving verification results to database."""
    
    def __init__(self, database):
        self.db = database
    
    def save_verification_results(self, check_id: int, results: Dict) -> Tuple[str, float]:
        """
        Save verification results from all services and calculate overall status.
        
        Args:
            check_id: VerificationCheck ID
            results: Dictionary with service results
        
        Returns:
            Tuple of (overall_status, confidence_score)
        """
        try:
            service_scores = []
            critical_issues = []
            warnings = []
            
            # Process each service result
            for service_name, result in results.items():
                # Convert data dict to JSON string
                data = result.get('data')
                data_json_str = json.dumps(data) if data else None
                
                # Save individual result
                check_result = CheckResult(
                    check_id=check_id,
                    service_name=service_name,
                    status=result.get('status', 'error'),
                    confidence_score=result.get('confidence', 0.0),
                    data_json=data_json_str,
                    error_message=result.get('error_message'),
                    response_time_ms=result.get('response_time_ms')
                )
                
                self.db.session.add(check_result)
                
                # Analyze result for overall calculation
                status = result.get('status', 'error')
                confidence = result.get('confidence', 0.0)
                
                if status == 'error':
                    critical_issues.append({
                        'service': service_name,
                        'confidence': confidence,
                        'data': result.get('data', {})
                    })
                elif status == 'warning':
                    warnings.append({
                        'service': service_name,
                        'confidence': confidence,
                        'data': result.get('data', {})
                    })
                
                service_scores.append({
                    'service': service_name,
                    'status': status,
                    'confidence': confidence,
                    'weight': self._get_service_weight(service_name)
                })
            
            # Commit individual results
            self.db.session.commit()
            
            # Calculate overall status and confidence
            overall_status, confidence_score = self._calculate_overall_assessment(
                service_scores, critical_issues, warnings
            )
            
            return overall_status, confidence_score
            
        except Exception as e:
            self.db.session.rollback()
            raise Exception(f"Error saving verification results: {str(e)}")
    
    def _get_service_weight(self, service_name: str) -> float:
        """
        Get weight for service in overall calculation.
        Different services have different importance levels.
        """
        weights = {
            'vies': 0.4,           # VAT validation is very important
            'sanctions': 0.35,      # Sanctions check is critical
            'handelsregister': 0.15, # German register is useful but not critical
            'registry_cz': 0.15,
            'registry_pl': 0.15,
            'insolvency': 0.1,     # Insolvency is important but less frequent
            'opencorporates': 0.05  # Additional verification
        }
        return weights.get(service_name, 0.1)
    
    def _calculate_overall_assessment(self, service_scores: list, critical_issues: list, warnings: list) -> Tuple[str, float]:
        """
        Calculate overall status and confidence based on all service results.
        
        Logic:
        - Any critical sanctions or major issues → 'error'
        - Multiple warnings or failed validations → 'warning'  
        - All checks passed → 'valid'
        """
        
        # Check for critical issues (sanctions, invalid VAT, etc.)
        sanctions_issues = [issue for issue in critical_issues if issue['service'] == 'sanctions']
        if sanctions_issues:
            # Sanctions found - critical problem
            highest_sanctions_confidence = max(issue['confidence'] for issue in sanctions_issues)
            return 'error', highest_sanctions_confidence
        
        vat_issues = [score for score in service_scores 
                     if score['service'] == 'vies' and score['status'] == 'error']
        if vat_issues and len(service_scores) > 1:
            # VAT invalid and we have other checks
            return 'error', 0.8
        
        # Check warning conditions
        warning_count = len(warnings)
        error_count = len(critical_issues) - len(sanctions_issues)  # Exclude already handled sanctions
        
        if warning_count >= 2 or (warning_count >= 1 and error_count >= 1):
            # Multiple warnings or warning + error
            avg_confidence = sum(score['confidence'] for score in service_scores) / len(service_scores)
            return 'warning', max(0.3, avg_confidence * 0.7)
        
        # Calculate weighted confidence score for valid status
        total_weight = 0
        weighted_confidence = 0
        
        for score in service_scores:
            weight = score['weight']
            confidence = score['confidence']
            
            # Reduce confidence for non-valid statuses
            if score['status'] == 'warning':
                confidence *= 0.8
            elif score['status'] == 'error':
                confidence *= 0.3
            
            weighted_confidence += confidence * weight
            total_weight += weight
        
        final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5
        
        # Determine final status
        if error_count == 0 and warning_count <= 1:
            return 'valid', final_confidence
        else:
            return 'warning', final_confidence * 0.8
    
    def get_verification_summary(self, check_id: int) -> Dict:
        """Get summary of verification results for a check."""
        try:
            results = CheckResult.query.filter_by(check_id=check_id).all()
            
            summary = {
                'total_services': len(results),
                'services_by_status': {
                    'valid': 0,
                    'warning': 0,
                    'error': 0
                },
                'average_response_time': 0,
                'services_details': []
            }
            
            total_response_time = 0
            response_count = 0
            
            for result in results:
                summary['services_by_status'][result.status] += 1
                
                if result.response_time_ms:
                    total_response_time += result.response_time_ms
                    response_count += 1
                
                summary['services_details'].append({
                    'service': result.service_name,
                    'status': result.status,
                    'confidence': result.confidence_score,
                    'has_data': bool(result.data),
                    'error': result.error_message,
                    'checked_at': result.created_at.isoformat()
                })
            
            if response_count > 0:
                summary['average_response_time'] = total_response_time / response_count
            
            return summary
            
        except Exception as e:
            return {
                'error': f"Error getting verification summary: {str(e)}",
                'check_id': check_id
            }
    
    def update_verification_confidence(self, check_id: int, new_confidence: float, reason: str = None):
        """Update verification confidence score with optional reason."""
        try:
            from crm.models import VerificationCheck
            
            check = VerificationCheck.query.get(check_id)
            if check:
                old_confidence = check.confidence_score
                check.confidence_score = new_confidence
                
                # Log confidence change
                confidence_result = CheckResult(
                    check_id=check_id,
                    service_name='confidence_update',
                    status='valid',
                    confidence_score=new_confidence,
                    data={
                        'old_confidence': old_confidence,
                        'new_confidence': new_confidence,
                        'reason': reason or 'Manual update',
                        'updated_at': datetime.utcnow().isoformat()
                    },
                    error_message=None
                )
                
                self.db.session.add(confidence_result)
                self.db.session.commit()
                
                return True
            
            return False
            
        except Exception as e:
            self.db.session.rollback()
            raise Exception(f"Error updating confidence: {str(e)}")
    
    def get_service_performance_stats(self) -> Dict:
        """Get performance statistics for all services."""
        try:
            from sqlalchemy import func
            
            # Query service statistics
            stats = self.db.session.query(
                CheckResult.service_name,
                func.count(CheckResult.id).label('total_checks'),
                func.avg(CheckResult.confidence_score).label('avg_confidence'),
                func.avg(CheckResult.response_time_ms).label('avg_response_time'),
                func.sum(func.case([(CheckResult.status == 'valid', 1)], else_=0)).label('valid_count'),
                func.sum(func.case([(CheckResult.status == 'warning', 1)], else_=0)).label('warning_count'),
                func.sum(func.case([(CheckResult.status == 'error', 1)], else_=0)).label('error_count')
            ).group_by(CheckResult.service_name).all()
            
            service_stats = {}
            for stat in stats:
                service_stats[stat.service_name] = {
                    'total_checks': stat.total_checks,
                    'avg_confidence': round(stat.avg_confidence or 0, 3),
                    'avg_response_time_ms': round(stat.avg_response_time or 0, 1),
                    'success_rate': round((stat.valid_count / stat.total_checks) * 100, 1) if stat.total_checks > 0 else 0,
                    'status_distribution': {
                        'valid': stat.valid_count,
                        'warning': stat.warning_count,
                        'error': stat.error_count
                    }
                }
            
            return {
                'services': service_stats,
                'generated_at': datetime.utcnow().isoformat(),
                'total_services': len(service_stats)
            }
            
        except Exception as e:
            return {
                'error': f"Error getting performance stats: {str(e)}"
            }