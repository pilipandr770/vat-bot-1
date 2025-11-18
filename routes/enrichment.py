"""
Enrichment API Routes - Автоматичне збагачення даних контрагента
Надає endpoint для frontend для автозаповнення форми верифікації.

Author: AI Assistant
Date: November 2025
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import logging

from services.enrichment_flow import EnrichmentOrchestrator
from crm.models import db, Company, Counterparty, VerificationCheck, CheckResult
from services.vies import VIESService
from services.business_registry import BusinessRegistryManager
from services.sanctions import SanctionsService
from crm.save_results import ResultsSaver

# Initialize services
results_saver = ResultsSaver(db)

logger = logging.getLogger(__name__)

enrichment_bp = Blueprint('enrichment', __name__, url_prefix='/api/enrichment')


@enrichment_bp.route('/enrich', methods=['POST'])
@login_required
def enrich_counterparty():
    """
    POST /api/enrichment/enrich
    
    Приймає частковi данi контрагента i повертає збагаченi данi.
    
    Request JSON:
    {
        "vat_number": "DE123456789",  // опціонально
        "email": "info@company.de",   // опціонально
        "domain": "company.de",        // опціонально
        "company_name": "Company GmbH", // опціонально
        "country_code": "DE"           // опціонально (для підказки)
    }
    
    Response JSON:
    {
        "success": true,
        "prefill": {
            "company_name": "Company GmbH",
            "company_address": "Hauptstr. 1",
            "company_city": "Berlin",
            "company_postal_code": "10115",
            "company_country": "DE",
            "counterparty_name": "Company GmbH",
            "counterparty_address": "Hauptstr. 1",
            "counterparty_website": "https://company.de",
            "counterparty_email": "info@company.de",
            "counterparty_phone": "+49 30 12345678"
        },
        "services": {
            "vat_lookup": {...},
            "osint": [...],
            "registry_de": {...}
        },
        "messages": [
            "VIES validation successful",
            "Business registry data found",
            "OSINT scan completed"
        ],
        "summary": {
            "sources_used": ["vies", "handelsregister", "osint"],
            "fields_filled": 10,
            "confidence": 0.85
        }
    }
    """
    try:
        data = request.get_json() or {}
        
        # Validation
        vat_number = data.get('vat_number', '').strip()
        email = data.get('email', '').strip()
        domain = data.get('domain', '').strip()
        company_name = data.get('company_name', '').strip()
        country_code = data.get('country_code', '').strip()
        
        if not any([vat_number, email, domain, company_name]):
            return jsonify({
                'success': False,
                'error': 'At least one of: vat_number, email, domain, or company_name is required'
            }), 400
        
        # Log request for debugging
        logger.info(f"Enrichment request from user {current_user.id}: "
                   f"VAT={vat_number}, email={email}, domain={domain}, "
                   f"company={company_name}, country={country_code}")
        
        # Run enrichment
        orchestrator = EnrichmentOrchestrator()
        result = orchestrator.enrich(
            vat_number=vat_number or None,
            email=email or None,
            domain=domain or None,
            company_name=company_name or None,
            country_code_hint=country_code or None
        )
        
        # Calculate summary stats
        prefill = result.get('prefill', {})
        services = result.get('services', {})
        messages = result.get('messages', [])
        
        summary = {
            'sources_used': list(services.keys()),
            'fields_filled': len([v for v in prefill.values() if v]),
            'confidence': _calculate_confidence(services)
        }
        
        # Log success
        logger.info(f"Enrichment completed: {summary['sources_used']} sources, "
                   f"{summary['fields_filled']} fields filled, "
                   f"confidence {summary['confidence']:.2f}")
        
        return jsonify({
            'success': result.get('success', False),
            'prefill': prefill,
            'services': services,
            'messages': messages,
            'summary': summary
        })
    
    except Exception as e:
        logger.error(f"Enrichment API error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Enrichment failed: {str(e)}'
        }), 500


@enrichment_bp.route('/auto-verify', methods=['POST'])
@login_required
def auto_verify():
    """
    POST /api/enrichment/auto-verify

    Advanced endpoint that combines enrichment with automatic verification.
    If enrichment finds sufficient data, automatically creates a verification check and saves to CRM.

    Request JSON:
    {
        "vat_number": "DE123456789",  // optional
        "email": "info@company.de",   // optional
        "domain": "company.de",        // optional
        "company_name": "Company GmbH", // optional
        "country_code": "DE",          // optional
        "company_vat": "DE999999999",  // user's company VAT (required for verification)
        "company_name": "My Company GmbH" // user's company name (required for verification)
    }

    Response JSON:
    {
        "success": true,
        "enrichment": {...},  // enrichment results
        "verification": {...}, // verification results (if auto-triggered)
        "saved_to_crm": true,  // whether data was saved to CRM
        "check_id": 123        // verification check ID
    }
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"AUTO-VERIFY REQUEST: authenticated={current_user.is_authenticated}, user_id={current_user.id if current_user.is_authenticated else 'None'}")
        
        data = request.get_json() or {}

        # Check quota before proceeding
        if not current_user.can_perform_verification():
            return jsonify({
                'success': False,
                'error': 'Sie haben Ihr Prüfungslimit erreicht.',
                'upgrade_required': True
            }), 403

        # Extract enrichment inputs
        vat_number = data.get('vat_number', '').strip()
        email = data.get('email', '').strip()
        domain = data.get('domain', '').strip()
        company_name = data.get('counterparty_name', '').strip()
        country_code = data.get('country_code', '').strip()

        # Extract company data (required for verification)
        company_vat = data.get('company_vat', '').strip()
        company_name_user = data.get('company_name', '').strip()

        if not any([vat_number, email, domain, company_name]):
            return jsonify({
                'success': False,
                'error': 'At least one of: vat_number, email, domain, or counterparty_name is required'
            }), 400

        # Log request
        logger.info(f"Auto-verify request from user {current_user.id}: "
                   f"VAT={vat_number}, email={email}, domain={domain}, "
                   f"company={company_name}, country={country_code}")

        # Step 1: Run enrichment
        orchestrator = EnrichmentOrchestrator()
        enrichment_result = orchestrator.enrich(
            vat_number=vat_number or None,
            email=email or None,
            domain=domain or None,
            company_name=company_name or None,
            country_code_hint=country_code or None
        )

        prefill = enrichment_result.get('prefill', {})
        services = enrichment_result.get('services', {})
        messages = enrichment_result.get('messages', [])

        summary = {
            'sources_used': list(services.keys()),
            'fields_filled': len([v for v in prefill.values() if v]),
            'confidence': _calculate_confidence(services)
        }

        response_data = {
            'success': enrichment_result.get('success', False),
            'enrichment': {
                'prefill': prefill,
                'services': services,
                'messages': messages,
                'summary': summary
            },
            'saved_to_crm': False
        }

        # Step 2: Check if we should auto-verify
        should_auto_verify = (
            enrichment_result.get('success') and
            summary['confidence'] >= 0.5 and  # At least 50% confidence
            company_vat and company_name_user  # User provided their company data
        )

        if should_auto_verify:
            try:
                # Prepare company data
                company_data = {
                    'vat_number': company_vat,
                    'company_name': company_name_user,
                    'legal_address': data.get('company_address', ''),
                    'email': data.get('company_email', ''),
                    'phone': data.get('company_phone', '')
                }

                # Prepare counterparty data from enrichment
                counterparty_data = {
                    'vat_number': prefill.get('counterparty_vat', vat_number or ''),
                    'company_name': prefill.get('counterparty_name', company_name or ''),
                    'address': prefill.get('counterparty_address', ''),
                    'email': email or '',
                    'domain': domain or prefill.get('counterparty_domain', ''),
                    'contact_person': data.get('counterparty_contact', ''),
                    'country': prefill.get('counterparty_country', country_code or '')
                }

                # Validate required fields
                if not company_data.get('vat_number') or not company_data.get('company_name'):
                    logger.warning("Missing company required fields for auto-verify")
                elif not counterparty_data.get('company_name') or not counterparty_data.get('country'):
                    logger.warning("Missing counterparty required fields for auto-verify")
                else:
                    # Create/get company and counterparty
                    company = _get_or_create_company(company_data, current_user.id)
                    counterparty = _get_or_create_counterparty(counterparty_data, current_user.id)

                    # Create verification check
                    verification_check = VerificationCheck(
                        company_id=company.id,
                        counterparty_id=counterparty.id,
                        user_id=current_user.id,
                        overall_status='pending'
                    )
                    db.session.add(verification_check)
                    db.session.commit()

                    # Run verification services
                    verification_results = _run_verification_services(counterparty_data)

                    # Increment user API usage
                    current_user.increment_api_usage()

                    # Save results and calculate overall status
                    overall_status, confidence = results_saver.save_verification_results(
                        verification_check.id, verification_results
                    )

                    # Update verification check
                    verification_check.overall_status = overall_status
                    verification_check.confidence_score = confidence
                    db.session.commit()

                    response_data.update({
                        'saved_to_crm': True,
                        'check_id': verification_check.id,
                        'verification': {
                            'overall_status': overall_status,
                            'confidence_score': confidence,
                            'results': verification_results
                        }
                    })

                    logger.info(f"Auto-verification completed for user {current_user.id}, check_id: {verification_check.id}")

            except Exception as verify_error:
                logger.error(f"Auto-verification failed: {str(verify_error)}", exc_info=True)
                # Don't fail the whole request if verification fails
                response_data['verification_error'] = str(verify_error)

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Auto-verify API error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Auto-verify failed: {str(e)}'
        }), 500


def _get_or_create_company(company_data, user_id):
    """Get existing company or create new one for current user."""
    company = Company.query.filter_by(
        vat_number=company_data['vat_number'],
        user_id=user_id
    ).first()

    if not company:
        company_data['user_id'] = user_id
        company = Company(**company_data)
        db.session.add(company)
        db.session.commit()

    return company


def _get_or_create_counterparty(counterparty_data, user_id):
    """Get existing counterparty or create new one for current user."""
    # Try to find by VAT number first
    counterparty = None
    if counterparty_data.get('vat_number'):
        counterparty = Counterparty.query.filter_by(
            vat_number=counterparty_data['vat_number'],
            user_id=user_id
        ).first()

    # If not found, try by name + country
    if not counterparty:
        counterparty = Counterparty.query.filter_by(
            company_name=counterparty_data['company_name'],
            country=counterparty_data['country'],
            user_id=user_id
        ).first()

    # Create new counterparty if not exists
    if not counterparty:
        counterparty_data['user_id'] = user_id
        counterparty = Counterparty(**counterparty_data)
        db.session.add(counterparty)
        db.session.commit()

    return counterparty


def _run_verification_services(counterparty_data):
    """Run all verification services."""
    results = {}

    # VIES VAT validation
    if counterparty_data.get('vat_number'):
        vies_service = VIESService()
        vies_result = vies_service.validate_vat(
            counterparty_data['country'],
            counterparty_data['vat_number']
        )
        results['vies'] = vies_result

    # Business registry lookup
    registry_manager = BusinessRegistryManager()
    registry_result = registry_manager.lookup(
        counterparty_data['country'],
        counterparty_data['company_name'],
        vat_number=counterparty_data.get('vat_number')
    )
    if registry_result:
        results[registry_result.get('source', f"registry_{counterparty_data['country'].lower()}")] = registry_result

    # Sanctions check
    sanctions_service = SanctionsService()
    sanctions_result = sanctions_service.check_sanctions(
        counterparty_data['company_name'],
        counterparty_data.get('contact_person', '')
    )
    results['sanctions'] = sanctions_result

    return results


@enrichment_bp.route('/enrich-by-vat', methods=['POST'])
@login_required
def enrich_by_vat():
    """
    POST /api/enrichment/enrich-by-vat
    
    Simplified endpoint - only VAT number required.
    
    Request JSON:
    {
        "vat_number": "DE123456789"
    }
    
    Response: Same as /enrich
    """
    try:
        data = request.get_json() or {}
        vat_number = data.get('vat_number', '').strip()
        
        if not vat_number:
            return jsonify({
                'success': False,
                'error': 'VAT number is required'
            }), 400
        
        # Extract country code hint if VAT has correct format
        country_code = vat_number[:2] if len(vat_number) > 2 else None
        
        orchestrator = EnrichmentOrchestrator()
        result = orchestrator.enrich(
            vat_number=vat_number,
            country_code_hint=country_code
        )
        
        prefill = result.get('prefill', {})
        services = result.get('services', {})
        messages = result.get('messages', [])
        
        summary = {
            'sources_used': list(services.keys()),
            'fields_filled': len([v for v in prefill.values() if v]),
            'confidence': _calculate_confidence(services)
        }
        
        return jsonify({
            'success': result.get('success', False),
            'prefill': prefill,
            'services': services,
            'messages': messages,
            'summary': summary
        })
    
    except Exception as e:
        logger.error(f"VAT enrichment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Enrichment failed: {str(e)}'
        }), 500


@enrichment_bp.route('/enrich-by-email', methods=['POST'])
@login_required
def enrich_by_email():
    """
    POST /api/enrichment/enrich-by-email
    
    Simplified endpoint - only email required (extracts domain for OSINT).
    
    Request JSON:
    {
        "email": "info@company.de"
    }
    
    Response: Same as /enrich
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Valid email is required'
            }), 400
        
        orchestrator = EnrichmentOrchestrator()
        result = orchestrator.enrich(email=email)
        
        prefill = result.get('prefill', {})
        services = result.get('services', {})
        messages = result.get('messages', [])
        
        summary = {
            'sources_used': list(services.keys()),
            'fields_filled': len([v for v in prefill.values() if v]),
            'confidence': _calculate_confidence(services)
        }
        
        return jsonify({
            'success': result.get('success', False),
            'prefill': prefill,
            'services': services,
            'messages': messages,
            'summary': summary
        })
    
    except Exception as e:
        logger.error(f"Email enrichment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Enrichment failed: {str(e)}'
        }), 500


def _calculate_confidence(services: dict) -> float:
    """
    Calculate confidence score based on number and quality of sources.
    
    Scoring:
    - VAT lookup (VIES): 0.4 points
    - Business registry: 0.3 points
    - OSINT: 0.3 points
    
    Max confidence: 1.0
    """
    confidence = 0.0
    
    # Check VAT lookup
    if 'vat_lookup' in services:
        vat_data = services['vat_lookup']
        if vat_data.get('prefill'):
            confidence += 0.4
    
    # Check business registries
    registry_keys = [k for k in services.keys() if k.startswith('registry_')]
    if registry_keys:
        confidence += 0.3
    
    # Check OSINT
    if 'osint' in services:
        osint_data = services['osint']
        if isinstance(osint_data, list) and len(osint_data) > 0:
            confidence += 0.3
    
    return min(confidence, 1.0)
