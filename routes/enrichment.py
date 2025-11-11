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
