"""
CRM Routes - Counterparty Management & Monitoring
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from crm.models import db, Counterparty, VerificationCheck, CheckResult, Alert
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

@crm_bp.route('/')
@login_required
def index():
    """CRM Dashboard - List all counterparties"""
    logger.info(f"=== CRM INDEX REQUEST ===")
    logger.info(f"User ID: {current_user.id}")
    logger.info(f"User email: {current_user.email}")
    
    counterparties = Counterparty.query.filter_by(user_id=current_user.id)\
        .order_by(Counterparty.created_at.desc()).all()
    
    logger.info(f"Found {len(counterparties)} counterparties for user {current_user.id}")
    
    # Debug: показать все counterparties в БД (для диагностики)
    all_counterparties = Counterparty.query.all()
    logger.debug(f"Total counterparties in DB: {len(all_counterparties)}")
    for cp in all_counterparties[:5]:  # Показать первые 5
        logger.debug(f"  - ID: {cp.id}, Name: {cp.company_name}, User ID: {cp.user_id}")
    
    # Get monitoring stats
    total_counterparties = len(counterparties)
    monitored_counterparties = sum(1 for c in counterparties 
                                   if VerificationCheck.query.filter_by(counterparty_id=c.id, is_monitoring_active=True).first())
    
    logger.info(f"Monitored counterparties: {monitored_counterparties}/{total_counterparties}")
    
    # Recent alerts
    recent_alerts = Alert.query.join(VerificationCheck)\
        .filter(VerificationCheck.user_id == current_user.id)\
        .order_by(Alert.created_at.desc())\
        .limit(10).all()
    
    logger.info(f"Found {len(recent_alerts)} recent alerts")
    
    return render_template('crm/index.html', 
                          counterparties=counterparties,
                          total_counterparties=total_counterparties,
                          monitored_counterparties=monitored_counterparties,
                          recent_alerts=recent_alerts)

@crm_bp.route('/counterparty/<int:counterparty_id>')
@login_required
def counterparty_details(counterparty_id):
    """View counterparty details and verification history"""
    counterparty = Counterparty.query.filter_by(id=counterparty_id, user_id=current_user.id).first_or_404()
    
    # Get all verification checks for this counterparty
    checks = VerificationCheck.query.filter_by(counterparty_id=counterparty_id)\
        .order_by(VerificationCheck.check_date.desc()).all()
    
    # Get alerts for this counterparty
    alerts = Alert.query.join(VerificationCheck)\
        .filter(VerificationCheck.counterparty_id == counterparty_id)\
        .order_by(Alert.created_at.desc()).all()
    
    return render_template('crm/counterparty_details.html',
                          counterparty=counterparty,
                          checks=checks,
                          alerts=alerts)

# ===========================
# API ENDPOINTS
# ===========================

@crm_bp.route('/api/counterparties', methods=['GET'])
@login_required
def api_list_counterparties():
    """Get list of all counterparties (with filtering)"""
    # Query params for filtering
    country = request.args.get('country')
    search = request.args.get('search')
    monitoring_only = request.args.get('monitoring_only') == 'true'
    
    query = Counterparty.query.filter_by(user_id=current_user.id)
    
    if country:
        query = query.filter_by(country=country)
    
    if search:
        query = query.filter(
            (Counterparty.company_name.ilike(f'%{search}%')) |
            (Counterparty.vat_number.ilike(f'%{search}%'))
        )
    
    if monitoring_only:
        # Get counterparties with active monitoring
        monitored_ids = [c.counterparty_id for c in 
                        VerificationCheck.query.filter_by(user_id=current_user.id, is_monitoring_active=True).all()]
        query = query.filter(Counterparty.id.in_(monitored_ids))
    
    counterparties = query.order_by(Counterparty.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'counterparties': [{
            'id': c.id,
            'vat_number': c.vat_number,
            'company_name': c.company_name,
            'country': c.country,
            'address': c.address,
            'email': c.email,
            'domain': c.domain,
            'contact_person': c.contact_person,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'is_monitoring': VerificationCheck.query.filter_by(counterparty_id=c.id, is_monitoring_active=True).first() is not None
        } for c in counterparties]
    })

@crm_bp.route('/api/counterparties/<int:counterparty_id>', methods=['GET'])
@login_required
def api_get_counterparty(counterparty_id):
    """Get single counterparty details"""
    counterparty = Counterparty.query.filter_by(id=counterparty_id, user_id=current_user.id).first()
    
    if not counterparty:
        return jsonify({'success': False, 'error': 'Counterparty not found'}), 404
    
    # Get latest check
    latest_check = VerificationCheck.query.filter_by(counterparty_id=counterparty_id)\
        .order_by(VerificationCheck.check_date.desc()).first()
    
    return jsonify({
        'success': True,
        'counterparty': {
            'id': counterparty.id,
            'vat_number': counterparty.vat_number,
            'company_name': counterparty.company_name,
            'country': counterparty.country,
            'address': counterparty.address,
            'email': counterparty.email,
            'domain': counterparty.domain,
            'contact_person': counterparty.contact_person,
            'created_at': counterparty.created_at.isoformat() if counterparty.created_at else None,
            'latest_check': {
                'id': latest_check.id,
                'check_date': latest_check.check_date.isoformat(),
                'overall_status': latest_check.overall_status,
                'confidence_score': latest_check.confidence_score,
                'is_monitoring_active': latest_check.is_monitoring_active
            } if latest_check else None
        }
    })

@crm_bp.route('/api/counterparties', methods=['POST'])
@login_required
def api_create_counterparty():
    """Create new counterparty"""
    data = request.get_json()
    
    # Validation
    required_fields = ['company_name', 'country']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
    
    # Check if counterparty already exists
    if data.get('vat_number'):
        existing = Counterparty.query.filter_by(
            user_id=current_user.id,
            vat_number=data['vat_number']
        ).first()
        if existing:
            return jsonify({'success': False, 'error': 'Counterparty with this VAT number already exists'}), 400
    
    # Create counterparty
    counterparty = Counterparty(
        user_id=current_user.id,
        vat_number=data.get('vat_number'),
        company_name=data['company_name'],
        country=data['country'],
        address=data.get('address'),
        email=data.get('email'),
        domain=data.get('domain'),
        contact_person=data.get('contact_person')
    )
    
    db.session.add(counterparty)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'counterparty_id': counterparty.id,
        'message': 'Counterparty created successfully'
    }), 201

@crm_bp.route('/api/counterparties/<int:counterparty_id>', methods=['PUT'])
@login_required
def api_update_counterparty(counterparty_id):
    """Update counterparty"""
    counterparty = Counterparty.query.filter_by(id=counterparty_id, user_id=current_user.id).first()
    
    if not counterparty:
        return jsonify({'success': False, 'error': 'Counterparty not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'vat_number' in data:
        counterparty.vat_number = data['vat_number']
    if 'company_name' in data:
        counterparty.company_name = data['company_name']
    if 'country' in data:
        counterparty.country = data['country']
    if 'address' in data:
        counterparty.address = data['address']
    if 'email' in data:
        counterparty.email = data['email']
    if 'domain' in data:
        counterparty.domain = data['domain']
    if 'contact_person' in data:
        counterparty.contact_person = data['contact_person']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Counterparty updated successfully'
    })

@crm_bp.route('/api/counterparties/<int:counterparty_id>', methods=['DELETE'])
@login_required
def api_delete_counterparty(counterparty_id):
    """Delete counterparty and all related data"""
    counterparty = Counterparty.query.filter_by(id=counterparty_id, user_id=current_user.id).first()
    
    if not counterparty:
        return jsonify({'success': False, 'error': 'Counterparty not found'}), 404
    
    # Store info for logging
    company_name = counterparty.company_name
    vat_number = counterparty.vat_number
    
    # Count related records before deletion
    checks_count = VerificationCheck.query.filter_by(counterparty_id=counterparty_id).count()
    
    try:
        # Delete related verification checks (cascade will handle check_results and alerts)
        VerificationCheck.query.filter_by(counterparty_id=counterparty_id).delete()
        
        # Delete counterparty
        db.session.delete(counterparty)
        db.session.commit()
        
        # Log the deletion
        from datetime import datetime
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Counterparty deleted: {company_name} (VAT: {vat_number}) by user {current_user.email}. "
                   f"Deleted {checks_count} verification checks and related data.")
        
        return jsonify({
            'success': True,
            'message': f'Counterparty "{company_name}" deleted successfully',
            'deleted_checks': checks_count
        })
    
    except Exception as e:
        db.session.rollback()
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting counterparty {counterparty_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500

@crm_bp.route('/api/counterparties/<int:counterparty_id>/monitoring', methods=['POST'])
@login_required
def api_toggle_monitoring(counterparty_id):
    """Enable/disable monitoring for counterparty"""
    counterparty = Counterparty.query.filter_by(id=counterparty_id, user_id=current_user.id).first()
    
    if not counterparty:
        return jsonify({'success': False, 'error': 'Counterparty not found'}), 404
    
    data = request.get_json()
    is_active = data.get('is_active', True)
    
    # Update monitoring status for latest check
    latest_check = VerificationCheck.query.filter_by(counterparty_id=counterparty_id)\
        .order_by(VerificationCheck.check_date.desc()).first()
    
    if latest_check:
        latest_check.is_monitoring_active = is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Monitoring {"enabled" if is_active else "disabled"} successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No verification checks found for this counterparty'
        }), 400

@crm_bp.route('/api/counterparties/duplicates', methods=['GET'])
@login_required
def api_find_duplicates():
    """Find potential duplicate counterparties"""
    from sqlalchemy import func
    
    # Find duplicates by VAT number
    vat_duplicates = db.session.query(
        Counterparty.vat_number,
        func.count(Counterparty.id).label('count')
    ).filter(
        Counterparty.user_id == current_user.id,
        Counterparty.vat_number.isnot(None),
        Counterparty.vat_number != ''
    ).group_by(
        Counterparty.vat_number
    ).having(
        func.count(Counterparty.id) > 1
    ).all()
    
    # Find duplicates by company name
    name_duplicates = db.session.query(
        Counterparty.company_name,
        func.count(Counterparty.id).label('count')
    ).filter(
        Counterparty.user_id == current_user.id,
        Counterparty.company_name.isnot(None)
    ).group_by(
        Counterparty.company_name
    ).having(
        func.count(Counterparty.id) > 1
    ).all()
    
    # Get full details of duplicates
    duplicates = {
        'vat_duplicates': [],
        'name_duplicates': [],
        'total_duplicates': 0
    }
    
    for vat, count in vat_duplicates:
        counterparties = Counterparty.query.filter_by(
            user_id=current_user.id,
            vat_number=vat
        ).all()
        duplicates['vat_duplicates'].append({
            'vat_number': vat,
            'count': count,
            'counterparties': [{
                'id': cp.id,
                'company_name': cp.company_name,
                'country': cp.country,
                'created_at': cp.created_at.isoformat()
            } for cp in counterparties]
        })
    
    for name, count in name_duplicates:
        counterparties = Counterparty.query.filter_by(
            user_id=current_user.id,
            company_name=name
        ).all()
        # Skip if already in VAT duplicates
        if not any(cp.vat_number for cp in counterparties if any(
            dup['vat_number'] == cp.vat_number for dup in duplicates['vat_duplicates']
        )):
            duplicates['name_duplicates'].append({
                'company_name': name,
                'count': count,
                'counterparties': [{
                    'id': cp.id,
                    'vat_number': cp.vat_number or 'N/A',
                    'country': cp.country,
                    'created_at': cp.created_at.isoformat()
                } for cp in counterparties]
            })
    
    duplicates['total_duplicates'] = len(duplicates['vat_duplicates']) + len(duplicates['name_duplicates'])
    
    return jsonify(duplicates)
