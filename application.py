import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_babel import Babel, gettext as _, lazy_gettext as _l
from config import config
from crm.models import db, VerificationCheck
from auth.models import User
from services.scheduler import init_scheduler, ensure_startup_blog_check
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import psycopg2

logger = logging.getLogger(__name__)

# Initialize Flask extensions
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
babel = Babel()

def is_ssl_error(exception):
    if isinstance(exception, OperationalError):
        error_msg = str(exception).lower()
        return any(keyword in error_msg for keyword in [
            'ssl error', 'ssl', 'decryption failed', 'bad record mac',
            'connection reset', 'server closed the connection'
        ])
    return False


def ensure_schema(app):
    """Create target PostgreSQL schema if missing to avoid runtime failures."""
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    schema = os.environ.get('DB_SCHEMA')

    if not schema or not database_uri.startswith('postgresql://'):
        return

    try:
        with app.app_context():
            engine = db.engine
            with engine.connect() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                connection.commit()
    except Exception as exc:  # pragma: no cover - defensive logging
        app.logger.error('Failed to ensure schema %s: %s', schema, exc)


def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    # Instantiate config so ProductionConfig.__init__ validation runs at call time
    _conf_cls = config[config_name]
    _conf_obj = _conf_cls() if isinstance(_conf_cls, type) else _conf_cls
    app.config.from_object(_conf_obj)

    # ── Defense-in-depth: block insecure defaults in production ───────────
    # Redundant second guard after ProductionConfig.__init__, but protects
    # against code paths that may skip instantiation.
    if config_name == 'production':
        _insecure_key = 'dev-secret-key-change-in-production'
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == _insecure_key:
            raise RuntimeError(
                'FATAL: Insecure or missing SECRET_KEY in production. '
                'Set the SECRET_KEY environment variable to a strong random value.'
            )
        if not app.config.get('MAILGUARD_ENCRYPTION_KEY'):
            raise RuntimeError(
                'FATAL: MAILGUARD_ENCRYPTION_KEY is required in production '
                'to protect IMAP/SMTP credentials.'
            )

    # ── Structured JSON logging ────────────────────────────────────────────
    if not app.debug:
        try:
            from pythonjsonlogger import jsonlogger
            handler = logging.StreamHandler()
            handler.setFormatter(jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            ))
            app.logger.handlers.clear()
            app.logger.addHandler(handler)
            app.logger.setLevel(logging.INFO)
        except ImportError:
            pass  # python-json-logger not installed — use default logging

    # ── Sentry error tracking ──────────────────────────────────────────────
    _sentry_dsn = app.config.get('SENTRY_DSN') or os.environ.get('SENTRY_DSN')
    if _sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            sentry_sdk.init(
                dsn=_sentry_dsn,
                integrations=[FlaskIntegration(), SqlalchemyIntegration()],
                environment=config_name,
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            app.logger.info('Sentry error tracking enabled.')
        except ImportError:
            app.logger.warning('sentry-sdk not installed; skipping Sentry init.')

    if not app.config.get('FILE_SCANNER_URL') or not app.config.get('FILE_SCANNER_ENABLED', True):
        app.logger.warning(
            'FILE_SCANNER_URL not configured or scanner disabled; MailGuard will rely on local heuristics.'
        )
    
    # Initialize extensions
    db.init_app(app)
    ensure_schema(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    
    # Configure Babel functions
    def get_locale():
        """Determine the best locale for the current request."""
        try:
            # Check if user has a preferred language in session
            from flask import session, request, has_request_context
            if has_request_context():
                # Check query parameter first (highest priority)
                lang_param = request.args.get('lang')
                if lang_param and lang_param in ['de', 'en', 'uk']:
                    return lang_param
                
                # Check if user has a preferred language in session
                user_locale = session.get('language')
                if user_locale and user_locale in ['de', 'en', 'uk']:
                    return user_locale
                
                # Check Accept-Language header
                return request.accept_languages.best_match(['de', 'en', 'uk'], default='de')
        except RuntimeError:
            # Outside of request context, return default
            pass
        
        return 'de'  # Default locale

    def get_timezone():
        """Determine the best timezone for the current request."""
        return 'Europe/Berlin'
    
    babel.init_app(app, 
                   locale_selector=get_locale,
                   timezone_selector=get_timezone,
                   default_locale='de',
                   default_timezone='Europe/Berlin',
                   default_domain='messages')
    
    # Set translation directory explicitly
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(app.root_path, 'translations')
    
    # Set selectors on app for template access
    app.babel_locale_selector = get_locale
    app.babel_timezone_selector = get_timezone
    
    # Create custom gettext function that respects session locale
    def session_gettext(message):
        """Gettext function that uses session locale."""
        from flask import session, has_request_context, request
        import gettext
        import os
        
        if has_request_context():
            # Check query parameter first (highest priority)
            lang_param = request.args.get('lang')
            if lang_param and lang_param in ['de', 'en', 'uk']:
                user_locale = lang_param
            else:
                # Check if user has a preferred language in session
                user_locale = session.get('language', 'de')
        else:
            user_locale = 'de'
        
        try:
            trans = gettext.translation('messages', 
                                      localedir=os.path.join(app.root_path, 'translations'),
                                      languages=[user_locale])
            return trans.gettext(message)
        except Exception:
            # Fallback to default
            return message
    
    # Override babel's gettext with our session-aware version
    babel.gettext = session_gettext
    babel.ngettext = lambda singular, plural, n: session_gettext(singular) if n == 1 else session_gettext(plural)
    
    # Add template context processor for session-aware gettext
    @app.context_processor
    def inject_gettext():
        def gettext_func(message):
            return session_gettext(message)
        return {'_': gettext_func}
    
    # Add template context processor for locale functions
    @app.context_processor
    def inject_locale():
        return {
            'get_locale': get_locale,
            'get_timezone': get_timezone
        }
    
    # Add to Jinja2 globals for macros
    app.jinja_env.globals.update(get_locale=get_locale)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access for AJAX requests."""
        import logging
        logger = logging.getLogger(__name__)
        content_type = request.headers.get('Content-Type', '')
        is_ajax = (
            request.is_json or 
            content_type == 'application/json' or 
            'application/x-www-form-urlencoded' in content_type or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )
        logger.error(f"UNAUTHORIZED: path={request.path}, method={request.method}, is_ajax={is_ajax}, content_type={content_type}, user_agent={request.headers.get('User-Agent', '')}")
        
        if is_ajax:
            return jsonify({
                'success': False,
                'error': 'Bitte melden Sie sich an, um diese Funktion zu nutzen.',
                'redirect': url_for('auth.login')
            }), 401
        return redirect(url_for('auth.login'))
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except Exception as e:
            # Handle SSL errors and database connection issues
            app.logger.error(f"Error loading user {user_id}: {str(e)}")
            # Return None to force re-authentication
            return None
    
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
    csrf.exempt(chatbot_bp)  # JSON API — no CSRF needed

    from services.sales_chatbot import sales_chatbot_bp
    app.register_blueprint(sales_chatbot_bp)
    csrf.exempt(sales_chatbot_bp)  # Public API — no CSRF needed

    from link_scanner.routes import link_scanner
    app.register_blueprint(link_scanner, url_prefix='/link-scanner')

    from app.mailguard import mailguard_bp
    app.register_blueprint(mailguard_bp)

    # TeamGuard — Team security management
    try:
        from app.teamguard.views import teamguard_bp
        app.register_blueprint(teamguard_bp)
    except Exception as e:
        app.logger.warning('TeamGuard blueprint not registered: %s', e)

    from app.pentesting.routes import pentesting
    app.register_blueprint(pentesting)

    # Register enrichment API blueprint
    from routes.enrichment import enrichment_bp
    app.register_blueprint(enrichment_bp)
    
    # Register CRM blueprint
    from crm.routes import crm_bp
    app.register_blueprint(crm_bp)

    # Register Programmatic SEO blueprint
    from programmatic.routes import programmatic_bp
    app.register_blueprint(programmatic_bp)

    # Phone intelligence blueprint (PhoneInfoga integration)
    try:
        from routes.phoneintel import phoneintel_bp
        app.register_blueprint(phoneintel_bp, url_prefix='/phoneintel')
    except Exception as e:
        app.logger.warning('PhoneIntel blueprint not registered: %s', e)

    # Register GEO + SME Trust blueprint
    from routes.geo_sme_routes import geo_bp
    app.register_blueprint(geo_bp)

    # Register Sitemap blueprint
    from routes.sitemap import sitemap_bp
    app.register_blueprint(sitemap_bp)

    # Register Blog blueprint
    from routes.blog import blog_bp
    app.register_blueprint(blog_bp)

    # Register EU Compliance Checker blueprint
    from compliance_checker.routes import compliance_checker_bp
    app.register_blueprint(compliance_checker_bp)

    # Register AI Consumer Panel blueprint
    from consumer_panel.routes import consumer_panel_bp
    app.register_blueprint(consumer_panel_bp)

    # Register NIS2 Compliance Platform blueprint
    try:
        from app.nis2 import nis2_bp
        app.register_blueprint(nis2_bp)
        from app.nis2.continuous_monitoring.scheduler import init_nis2_monitoring_scheduler
        init_nis2_monitoring_scheduler(app)
    except Exception as _nis2_exc:
        app.logger.warning('NIS2 blueprint not registered: %s', _nis2_exc)
    # Init scheduler (only in production/when not in debug reload)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        try:
            init_scheduler(app=app)
        except Exception as _sched_exc:
            app.logger.error('MonitoringScheduler failed to start: %s', _sched_exc, exc_info=True)
            app._scheduler_init_error = _sched_exc
            # Scheduler failed but we still want today's blog post on cold start
            try:
                ensure_startup_blog_check(app)
            except Exception:
                pass
        try:
            from app.mailguard.scheduler import setup_mailguard_scheduler
            app.mailguard_scheduler = setup_mailguard_scheduler(app)
        except Exception as _sched_exc:
            app.logger.error('MailGuard scheduler failed to start: %s', _sched_exc, exc_info=True)
        try:
            from crm.monitoring_scheduler import init_monitoring_scheduler
            app.crm_monitoring_scheduler = init_monitoring_scheduler(app)
        except Exception as _sched_exc:
            app.logger.error('CRM monitoring scheduler failed to start: %s', _sched_exc, exc_info=True)
    
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
    
    # Register main routes (landing, dashboard, verify, history, etc.)
    from routes.main import register_routes as _register_main_routes
    _register_main_routes(app)

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
            "connect-src 'self' https://cdn.jsdelivr.net https://accounts.google.com https://login.microsoftonline.com; "
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
    
    # Add error handler for database SSL errors
    @app.errorhandler(OperationalError)
    def handle_db_error(error):
        """Handle database connection errors, especially SSL issues."""
        if is_ssl_error(error):
            app.logger.error(f"SSL Database Error: {str(error)}")
            # Try to recover by disposing the connection pool
            try:
                db.session.rollback()
                db.engine.dispose()
            except:
                pass
            
            # Return user-friendly error for JSON requests
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Datenbankverbindungsfehler. Bitte versuchen Sie es erneut.',
                    'retry': True
                }), 500
            
            # For HTML requests
            flash('Datenbankverbindungsfehler. Bitte laden Sie die Seite neu.', 'error')
            return redirect(request.referrer or url_for('landing'))
        
        # Re-raise if not SSL error
        raise error

    # ── Flask CLI Commands ──────────────────────────────────────────────────
    import click

    @app.cli.command('generate-blog')
    @click.option('--force', is_flag=True, default=False,
                  help='Force generation even if post already exists today')
    def generate_blog_cmd(force):
        """Generate today's SEO blog post via Claude."""
        from services.blog_generator import generate_daily_blog_post
        try:
            result = generate_daily_blog_post(app, force=force)
            if result:
                click.echo(click.style('Blog post generated successfully.', fg='green'))
            else:
                click.echo(click.style(
                    'Skipped: post already exists today or Claude returned nothing.', fg='yellow'))
        except Exception as e:
            click.echo(click.style(f'Error: {e}', fg='red'))
            raise SystemExit(1)

    @app.cli.command('audit-admins')
    def audit_admins():
        """List all users with admin privileges — run this after any security incident."""
        from auth.models import User
        admins = User.query.filter_by(is_admin=True).order_by(User.created_at.desc()).all()
        if not admins:
            click.echo(click.style('No admin users found.', fg='yellow'))
            return
        click.echo(click.style(f'Found {len(admins)} admin user(s):', fg='cyan'))
        for u in admins:
            click.echo(f'  id={u.id}  email={u.email}  created={u.created_at}  active={u.is_active}')

    @app.cli.command('promote-admin')
    @click.argument('email')
    def promote_admin_cmd(email):
        """Grant admin rights to an existing user by EMAIL."""
        from auth.models import User
        user = User.query.filter_by(email=email.strip().lower()).first()
        if not user:
            click.echo(click.style(f"User '{email}' not found.", fg='red'), err=True)
            raise SystemExit(1)
        user.is_admin = True
        db.session.commit()
        click.echo(click.style(f"'{email}' is now admin.", fg='green'))

    @app.cli.command('init-db')
    def init_db():
        """Initialize database tables (use flask db upgrade in production)."""
        db.create_all()
        click.echo(click.style('Database initialized.', fg='green'))

    # ── Health check endpoints ─────────────────────────────────────────────
    @app.route('/healthz')
    def healthz():
        """Liveness probe: application is running."""
        return jsonify({'status': 'ok'}), 200

    @app.route('/readyz')
    def readyz():
        """Readiness probe: application can serve traffic (DB + Redis reachable)."""
        checks = {}
        http_status = 200
        try:
            db.session.execute(db.text('SELECT 1'))
            checks['database'] = 'ok'
        except Exception as e:
            checks['database'] = f'error: {e}'
            http_status = 503
        try:
            import redis as _redis
            _r = _redis.from_url(app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
                                 socket_connect_timeout=2)
            _r.ping()
            checks['redis'] = 'ok'
        except Exception as e:
            checks['redis'] = f'error: {e}'
            # Redis is optional — do not mark as unready
        return jsonify({'status': 'ok' if http_status == 200 else 'degraded', 'checks': checks}), http_status

    return app

# Create app instance for WSGI servers (Gunicorn, etc.)
app = create_app()

# For development server
if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_ENV') == 'development', host='127.0.0.1', port=5000)


