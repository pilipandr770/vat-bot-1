from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required

phoneintel_bp = Blueprint('phoneintel', __name__)


@phoneintel_bp.route('/')
@login_required
def phoneintel_ui():
    return render_template('phoneintel/analyze.html')


@phoneintel_bp.route('/api/analyze', methods=['POST'])
@login_required
def analyze_api():
    from app.services.phoneintel import get_service  # Local import to avoid circular dependency
    
    data = request.get_json() or {}
    phone = data.get('phone_number') or data.get('phone')
    country = data.get('country')

    if not phone:
        return jsonify({'success': False, 'error': 'phone_number is required'}), 400

    svc = get_service()
    try:
        result = svc.analyze(phone, country_hint=country)
    except Exception as e:
        current_app.logger.exception('Phone intelligence analysis failed')
        return jsonify({'success': False, 'error': 'analysis_failed'}), 500

    # IMPORTANT: Do not return/store any personally identifying information.
    return jsonify({'success': True, 'data': result})
