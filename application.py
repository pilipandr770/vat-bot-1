import os
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from config import config
from crm.models import db, Company, Counterparty, VerificationCheck, CheckResult
from auth.models import User
from services.vies import VIESService
from services.handelsregister import HandelsregisterService
from services.sanctions import SanctionsService
from crm.save_results import ResultsSaver
from file_scanner.routes import file_scanner
import asyncio
from datetime import datetime

# Initialize Flask extensions
login_manager = LoginManager()
mail = Mail()

def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    from auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from payments.routes import payments_bp
    app.register_blueprint(payments_bp, url_prefix='/payments')
    
    from payments.webhooks import webhooks_bp
    app.register_blueprint(webhooks_bp, url_prefix='/webhooks')
    
    from admin.routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from legal.routes import legal_bp
    app.register_blueprint(legal_bp, url_prefix='/legal')
    
    from services.osint_routes import osint_bp
    app.register_blueprint(osint_bp, url_prefix='/osint')
    
    from services.chatbot_routes import chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
    
    from file_scanner.routes import file_scanner
    app.register_blueprint(file_scanner, url_prefix='/file-scanner')
    
    from app.mailguard import mailguard_bp
    app.register_blueprint(mailguard_bp)
    
    # Register CRM blueprint
    from crm.routes import crm_bp
    app.register_blueprint(crm_bp)
    
    # Initialize monitoring services
    from services.alerts import init_alert_service
    from services.scheduler import init_scheduler
    
    # Init alert service with mail
    init_alert_service(mail)
    
    # Init scheduler (only in production/when not in debug reload)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        init_scheduler()
    
    # Mailguard models use the same db instance
    
    # Add Jinja2 filter for JSON formatting
    import json
    @app.template_filter('tojsonpretty')
    def to_json_pretty(value):
        return json.dumps(value, indent=2, ensure_ascii=False)
    
    # Add context processor for current date
    @app.context_processor
    def inject_current_date():
        return {'current_date': datetime.now()}
    
    # Initialize services
    vies_service = VIESService()
    handelsregister_service = HandelsregisterService()
    sanctions_service = SanctionsService()
    results_saver = ResultsSaver(db)
    
    @app.route('/')
    def landing():
        """Landing page for non-authenticated users."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('landing.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main verification interface for authenticated users."""
        subscription = current_user.active_subscription
        
        # Get user statistics
        total_checks = current_user.verifications.count()
        monthly_checks = current_user.get_monthly_verification_count()
        
        # Get recent verifications
        recent_checks = current_user.verifications.order_by(
            VerificationCheck.check_date.desc()
        ).limit(5).all()
        
        # Get recent CRM alerts
        from crm.models import Alert
        recent_alerts = Alert.query.join(VerificationCheck)\
            .filter(VerificationCheck.user_id == current_user.id)\
            .order_by(Alert.created_at.desc())\
            .limit(5).all()
        
        return render_template('index.html',
                             subscription=subscription,
                             total_checks=total_checks,
                             monthly_checks=monthly_checks,
                             recent_checks=recent_checks,
                             recent_alerts=recent_alerts)
    
    @app.route('/test')
    def test_form():
        """Simple test form for debugging."""
        return render_template('test_form.html')
    
    @app.route('/verify', methods=['POST'])
    def verify_counterparty():
        """Process verification request - requires authentication."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Check authentication manually for AJAX requests
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Bitte melden Sie sich an, um diese Funktion zu nutzen.',
                'redirect': url_for('auth.login')
            }), 401
        
        # Check if user can perform verification (quota check)
        if not current_user.can_perform_verification():
            # Get current usage info for better error message
            sub = current_user.active_subscription
            if not sub:
                # Free plan
                current_usage = current_user.get_monthly_verification_count()
                limit = 5
                plan_name = "Free"
            else:
                # Paid plan
                current_usage = sub.api_calls_used
                limit = sub.api_calls_limit if sub.api_calls_limit != -1 else "unlimited"
                plan_name = sub.plan
            
            return jsonify({
                'success': False,
                'error': f'Sie haben Ihr Prüfungslimit erreicht ({current_usage}/{limit}). Bitte upgraden Sie Ihren Plan.',
                'current_plan': plan_name,
                'current_usage': current_usage,
                'limit': limit,
                'upgrade_required': True
            }), 403
        
        try:
            # Log request details
            logger.info(f"=== VERIFICATION REQUEST ===")
            logger.info(f"Content-Type: {request.content_type}")
            logger.info(f"is_json: {request.is_json}")
            logger.info(f"ALL form data: {dict(request.form)}")
            logger.info(f"Form keys: {list(request.form.keys())}")
            logger.info(f"JSON data: {request.get_json(silent=True)}")
            
            # Extract form data (support both JSON and form data)
            if request.is_json:
                data = request.get_json()
                company_data = {
                    'vat_number': data.get('company_vat'),
                    'company_name': data.get('company_name'),
                    'legal_address': data.get('company_address'),
                    'email': data.get('company_email'),
                    'phone': data.get('company_phone')
                }
                
                counterparty_data = {
                    'vat_number': data.get('counterparty_vat'),
                    'company_name': data.get('counterparty_name'),
                    'address': data.get('counterparty_address'),
                    'email': data.get('counterparty_email'),
                    'domain': data.get('counterparty_domain'),
                    'contact_person': data.get('counterparty_contact'),
                    'country': data.get('counterparty_country')
                }
            else:
                company_data = {
                    'vat_number': request.form.get('company_vat', ''),
                    'company_name': request.form.get('company_name', ''),
                    'legal_address': request.form.get('company_address', ''),
                    'email': request.form.get('company_email', ''),
                    'phone': request.form.get('company_phone', '')
                }
                
                counterparty_data = {
                    'vat_number': request.form.get('counterparty_vat', ''),
                    'company_name': request.form.get('counterparty_name', ''),
                    'address': request.form.get('counterparty_address', ''),
                    'email': request.form.get('counterparty_email', ''),
                    'domain': request.form.get('counterparty_domain', ''),
                    'contact_person': request.form.get('counterparty_contact', ''),
                    'country': request.form.get('counterparty_country', '')
                }
            
            # Validate required fields
            logger.debug(f"Company data: {company_data}")
            logger.debug(f"Counterparty data: {counterparty_data}")
            
            if not company_data.get('vat_number') or not company_data.get('company_name'):
                logger.warning("Missing company required fields")
                return jsonify({'success': False, 'error': 'Company VAT and name are required'}), 400
            
            if not counterparty_data.get('company_name') or not counterparty_data.get('country'):
                logger.warning(f"Missing counterparty required fields. Name: {counterparty_data.get('company_name')}, Country: {counterparty_data.get('country')}")
                return jsonify({'success': False, 'error': 'Counterparty name and country are required'}), 400
            
            # Save or get company and counterparty (with user_id for multi-tenancy)
            company = get_or_create_company(company_data, current_user.id)
            counterparty = get_or_create_counterparty(counterparty_data, current_user.id)
            
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
            verification_results = run_verification_services(counterparty_data)
            
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
            
            return jsonify({
                'success': True,
                'check_id': verification_check.id,
                'overall_status': overall_status,
                'confidence_score': confidence,
                'results': verification_results
            })
            
        except Exception as e:
            import traceback
            logger.error(f"Error in verify_counterparty: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"Error in verify_counterparty: {str(e)}")
            print(traceback.format_exc())
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/history')
    def verification_history():
        """Display verification history."""
        page = request.args.get('page', 1, type=int)
        checks = VerificationCheck.query.order_by(
            VerificationCheck.check_date.desc()
        ).paginate(
            page=page, per_page=20, error_out=False
        )
        return render_template('history.html', checks=checks)
    
    @app.route('/check/<int:check_id>')
    def check_details(check_id):
        """Display detailed check results."""
        check = VerificationCheck.query.get_or_404(check_id)
        return render_template('check_details.html', check=check)
    
    @app.route('/api/check/<int:check_id>/results')
    def api_check_results(check_id):
        """API endpoint for check results."""
        check = VerificationCheck.query.get_or_404(check_id)
        results = {}
        for result in check.check_results:
            results[result.service_name] = {
                'status': result.status,
                'confidence_score': result.confidence_score,
                'data': result.data,
                'error_message': result.error_message,
                'response_time_ms': result.response_time_ms,
                'created_at': result.created_at.isoformat()
            }
        
        return jsonify({
            'check_id': check.id,
            'overall_status': check.overall_status,
            'confidence_score': check.confidence_score,
            'results': results
        })
    
    def get_or_create_company(company_data, user_id):
        """Get existing company or create new one for current user."""
        # Search only within user's companies (multi-tenant)
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
    
    def get_or_create_counterparty(counterparty_data, user_id):
        """Get existing counterparty or create new one for current user."""
        # Try to find by VAT number first (within user's counterparties)
        counterparty = None
        if counterparty_data.get('vat_number'):
            counterparty = Counterparty.query.filter_by(
                vat_number=counterparty_data['vat_number'],
                user_id=user_id
            ).first()
        
        # If not found, try by name + country (within user's counterparties)
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
    
    def run_verification_services(counterparty_data):
        """Run all verification services."""
        results = {}
        
        # VIES VAT validation
        if counterparty_data.get('vat_number'):
            vies_result = vies_service.validate_vat(
                counterparty_data['country'],
                counterparty_data['vat_number']
            )
            results['vies'] = vies_result
        
        # Handelsregister (for German companies)
        if counterparty_data['country'].upper() == 'DE':
            handelsregister_result = handelsregister_service.check_company(
                counterparty_data['company_name']
            )
            results['handelsregister'] = handelsregister_result
        
        # Sanctions check
        sanctions_result = sanctions_service.check_sanctions(
            counterparty_data['company_name'],
            counterparty_data.get('contact_person', '')
        )
        results['sanctions'] = sanctions_result
        
        return results
    
    # CLI commands for database management
    @app.cli.command()
    def init_db():
        """Initialize database."""
        db.create_all()
        print("Database initialized!")
    
    @app.cli.command()
    def test_apis():
        """Test all external API connections."""
        print("Testing VIES API...")
        vies_result = vies_service.validate_vat('DE', '123456789')
        print(f"VIES result: {vies_result['status']}")
        
        print("Testing Sanctions API...")
        sanctions_result = sanctions_service.check_sanctions('Test Company', '')
        print(f"Sanctions result: {sanctions_result['status']}")
        
        print("All API tests completed!")
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add comprehensive security headers to all responses."""
        
        # Content Security Policy - allow Bootstrap CDN and OAuth providers
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' cdn.jsdelivr.net 'unsafe-inline'; "
            "font-src 'self' cdn.jsdelivr.net data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://accounts.google.com https://login.microsoftonline.com; "
            "frame-src 'self' https://accounts.google.com https://login.microsoftonline.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests"
        )
        response.headers['Content-Security-Policy'] = csp_policy
        
        # Prevent clickjacking attacks
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Force HTTPS with HSTS (63072000 seconds = 2 years)
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        
        # Prevent sensitive data caching
        if request.endpoint and any(x in request.endpoint for x in ['verify', 'crm', 'mailguard', 'admin']):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        else:
            response.headers['Cache-Control'] = 'public, max-age=3600'
        
        # Additional security headers
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response
    
    return app

# Create app instance for WSGI servers (Gunicorn, etc.)
app = create_app()

# For development server
if __name__ == '__main__':
    app.run(debug=True)