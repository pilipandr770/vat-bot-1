import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration with Schema Support (PostgreSQL-first)
    default_pg_url = os.environ.get(
        'LOCAL_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/vat_bot_dev',
    )
    database_url = os.environ.get('DATABASE_URL') or default_pg_url

    # Fix for Render.com: postgres:// -> postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PostgreSQL Schema and Connection Settings
    # SSL fix for Render: Add pool_pre_ping and SSL mode
    engine_options = {
        'pool_pre_ping': True,  # Test connections before using
        'pool_recycle': 300,    # Recycle connections after 5 minutes
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # Add schema search path if PostgreSQL
    if database_url.startswith('postgresql://'):
        connect_args = {
            'options': f'-csearch_path={os.environ.get("DB_SCHEMA", "public")}',
            'connect_timeout': 10
        }
        
        # For Render: Add SSL settings to prevent SSL errors
        if 'render.com' in database_url or os.environ.get('RENDER'):
            connect_args['sslmode'] = 'require'
        
        engine_options['connect_args'] = connect_args
    
    SQLALCHEMY_ENGINE_OPTIONS = engine_options
    
    # Canonical site URL \u2014 used for blog/LinkedIn auto-post links.
    # Set SITE_BASE_URL env var in Render to override (e.g. https://vat-verifizierung.de).
    BASE_URL = os.environ.get('SITE_BASE_URL', 'https://vat-verifizierung.de')

    # API Keys
    VIES_API_KEY = os.environ.get('VIES_API_KEY')
    HANDELSREGISTER_API_KEY = os.environ.get('HANDELSREGISTER_API_KEY')
    
    # Internationalization (i18n) Configuration
    BABEL_DEFAULT_LOCALE = 'de'  # German as default
    BABEL_DEFAULT_TIMEZONE = 'Europe/Berlin'
    BABEL_SUPPORTED_LOCALES = ['de', 'en', 'uk']  # German, English, Ukrainian
    BABEL_DOMAIN = 'messages'
    
    # Translation paths
    BABEL_TRANSLATION_DIRECTORIES = './translations'
    OPENCORPORATES_API_KEY = os.environ.get('OPENCORPORATES_API_KEY')
    SANCTIONS_API_KEY = os.environ.get('SANCTIONS_API_KEY')
    VIRUSTOTAL_API_KEY = os.environ.get('VIRUSTOTAL_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GOOGLE_SAFE_BROWSING_API_KEY = os.environ.get('GOOGLE_SAFE_BROWSING_API_KEY')

    # External security scanners
    FILE_SCANNER_URL = os.environ.get('FILE_SCANNER_URL')
    FILE_SCANNER_ENABLED = os.environ.get('FILE_SCANNER_ENABLED', 'true').lower() not in {'0', 'false', 'no'}
    FILE_SCANNER_TIMEOUT = int(os.environ.get('FILE_SCANNER_TIMEOUT', 30))
    FILE_SCANNER_TOKEN = os.environ.get('FILE_SCANNER_TOKEN')
    
    # Flask-Mail / SMTP Configuration (single source of truth)
    MAIL_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('SMTP_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
    MAIL_USERNAME = os.environ.get('SMTP_USERNAME')
    MAIL_PASSWORD = os.environ.get('SMTP_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@vatverification.com')

    # Aliases for code that references SMTP_* directly
    SMTP_SERVER = MAIL_SERVER
    SMTP_PORT = MAIL_PORT
    SMTP_USERNAME = MAIL_USERNAME
    SMTP_PASSWORD = MAIL_PASSWORD

    # Notification Settings
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    # Stripe Configuration
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # Stripe Subscription Price IDs
    STRIPE_PRICE_BASIC = os.environ.get('STRIPE_PRICE_BASIC')
    STRIPE_PRICE_PROFESSIONAL = os.environ.get('STRIPE_PRICE_PROFESSIONAL')
    STRIPE_PRICE_ENTERPRISE = os.environ.get('STRIPE_PRICE_ENTERPRISE')
    
    # MailGuard OAuth Configuration
    GMAIL_CLIENT_ID = os.environ.get('GMAIL_CLIENT_ID')
    GMAIL_CLIENT_SECRET = os.environ.get('GMAIL_CLIENT_SECRET')
    MS_CLIENT_ID = os.environ.get('MS_CLIENT_ID')
    MS_CLIENT_SECRET = os.environ.get('MS_CLIENT_SECRET')
    MS_TENANT_ID = os.environ.get('MS_TENANT_ID', 'common')
    MAILGUARD_ENCRYPTION_KEY = os.environ.get('MAILGUARD_ENCRYPTION_KEY')
    
    # Redis and Celery
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Monitoring
    MONITORING_INTERVAL_HOURS = int(os.environ.get('MONITORING_INTERVAL_HOURS', 24))
    ALERT_THRESHOLD = float(os.environ.get('ALERT_THRESHOLD', 0.5))

    # Error tracking
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    # CORS / Origin controls for CSRF-exempt JSON endpoints
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'

    def __init__(self):
        _required = {
            'SECRET_KEY': os.environ.get('SECRET_KEY'),
            'DATABASE_URL': os.environ.get('DATABASE_URL'),
            'MAILGUARD_ENCRYPTION_KEY': os.environ.get('MAILGUARD_ENCRYPTION_KEY'),
        }
        missing = [k for k, v in _required.items() if not v or v == 'dev-secret-key-change-in-production']
        if missing:
            raise RuntimeError(
                f"Production startup blocked. Missing or insecure environment variables: {', '.join(missing)}. "
                "Set them before deploying."
            )

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    # SQLite doesn't support pool_size/max_overflow — use minimal engine options
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
