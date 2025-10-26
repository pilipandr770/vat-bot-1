# Counterparty Verification System - AI Development Guide

## Project Overview
Flask SaaS platform for automated EU business partner verification. Validates VAT numbers, checks sanctions lists, performs OSINT scans, and provides subscription-based access control.

## Architecture & Core Patterns

### Application Structure
```
├── app.py                 # Main Flask app with blueprint registration
├── config.py             # Environment-based configuration classes
├── crm/models.py         # SQLAlchemy models (Company, Counterparty, VerificationCheck)
├── auth/models.py        # User authentication & subscription models
├── services/             # External API integrations
│   ├── vies.py          # EU VAT validation (SOAP API)
│   ├── handelsregister.py # German business register
│   ├── sanctions.py     # EU/OFAC/UK sanctions lists
│   └── osint/           # Open Source Intelligence scanner
└── templates/            # 3-column UI layout (company|counterparty|results)
```

### Key Design Patterns

#### 1. Service Integration Pattern (`services/*.py`)
```python
class VIESService:
    def validate_vat(self, country_code: str, vat_number: str) -> Dict:
        # Standardized response format
        return {
            "status": "valid|warning|error",
            "source": "vies",
            "data": {...},
            "last_checked": "2025-10-02T10:30:00Z",
            "confidence": 0.95
        }
```

#### 2. Blueprint Route Organization
```python
# auth/routes.py - Authentication endpoints
auth_bp = Blueprint('auth', __name__)
@auth_bp.route('/login', methods=['GET', 'POST'])
def login(): ...

# Main routes in app.py with @login_required
@app.route('/verify', methods=['POST'])
def verify_counterparty(): ...
```

#### 3. OSINT Adapter Pattern (`services/osint/`)
```python
class OsintScanner:
    def run_all(self) -> List[Dict]:
        adapters = [WhoisAdapter, DnsAdapter, SslLabsAdapter, ...]
        results = []
        for adapter in adapters:
            result = adapter(target).run()
            results.append(result)
        return results
```

## Critical Developer Workflows

### Environment Setup (Required First)
```bash
# 1. Clone and setup virtual environment
git clone <repo>
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment configuration (.env)
FLASK_ENV=development
DATABASE_URL=sqlite:///counterparty_verification.db
SECRET_KEY=your-secret-key
# API keys for external services...

# 4. Database initialization
flask db init
flask db migrate -m "Initial setup"
flask db upgrade

# 5. Start development server
flask run --debug
```

### Database Schema Management
- **Models**: `crm/models.py` (Company, Counterparty, VerificationCheck, CheckResult)
- **Migrations**: Use `flask db migrate/upgrade` for schema changes
- **Multi-tenant**: PostgreSQL schemas for production isolation
- **Relationships**: User → VerificationCheck → CheckResult (cascading deletes)

### Subscription & Quota System
```python
# User model methods (auth/models.py)
def can_perform_verification(self):
    sub = self.active_subscription
    if not sub:
        return self.get_monthly_verification_count() < 5  # Free tier: 5/month
    return sub.api_calls_used < sub.api_calls_limit

# Quota exceeded response (app.py)
return jsonify({
    'success': False,
    'error': f'Sie haben Ihr Prüfungslimit erreicht ({usage}/{limit}).',
    'upgrade_required': True
}), 403
```

## Project-Specific Conventions

### UI/UX Patterns
- **3-Column Layout**: Company data | Counterparty data | Results panel
- **German Interface**: All user-facing text in German (`Bitte melden Sie sich an...`)
- **Status Indicators**: ✅ Valid, ⚠️ Warning, ❌ Error
- **Form Validation**: Client-side + server-side with German error messages

### API Integration Standards
- **Response Format**: Consistent `{"status": "valid|warning|error", "data": {...}, "confidence": 0.95}`
- **Error Handling**: Try/catch with logging, graceful degradation
- **Rate Limiting**: Built-in delays and backoff strategies
- **Caching**: Redis for API responses (TTL: 24h)

### Authentication Flow
```python
# Manual auth check for AJAX endpoints (not @login_required)
if not current_user.is_authenticated:
    return jsonify({'error': 'Auth required', 'redirect': '/auth/login'}), 401

# Quota check before processing
if not current_user.can_perform_verification():
    return jsonify({'error': 'Quota exceeded', 'upgrade_required': True}), 403
```

## Development Commands & Scripts

### Database Operations
```bash
flask db migrate -m "Add new field"  # Create migration
flask db upgrade                     # Apply migrations
flask db downgrade                   # Rollback
```

### Testing & Debugging
```bash
# Run with debug mode
flask run --debug

# Check API connectivity
python -c "from services.vies import VIESService; print(VIESService().validate_vat('DE', '123456789'))"

# Database shell
flask shell
>>> from crm.models import db, User
>>> User.query.all()
```

### Production Deployment
```bash
# Environment variables required
FLASK_ENV=production
DATABASE_URL=postgresql://...
SECRET_KEY=...
STRIPE_SECRET_KEY=...
# API keys for all services...

# Gunicorn for production
gunicorn app:app --bind 0.0.0.0:10000
```

## Common Development Tasks

### Adding New Verification Service
1. Create `services/new_service.py` with standardized response format
2. Add to `crm/save_results.py` processing logic
3. Update frontend JavaScript in `static/js/app.js`
4. Add to database models if needed

### Adding New Subscription Plan
1. Update Stripe dashboard with new price
2. Add plan logic in `payments/routes.py`
3. Update quota checks in `auth/models.py`
4. Update UI pricing display

### Debugging API Issues
```python
# Check service logs
import logging
logger = logging.getLogger(__name__)
logger.info(f"API Response: {response.json()}")

# Test service isolation
from services.vies import VIESService
service = VIESService()
result = service.validate_vat('DE', '123456789')
print(f"Status: {result['status']}")
```

## File Organization Guidelines

- **Routes**: Blueprint in separate files (`auth/routes.py`, `payments/routes.py`)
- **Models**: Domain separation (`crm/models.py` for business logic, `auth/models.py` for users)
- **Services**: One class per external API (`services/vies.py`, `services/sanctions.py`)
- **Templates**: Organized by feature (`templates/auth/`, `templates/payments/`)
- **Static Assets**: `static/css/`, `static/js/`, `static/images/`

## Security & Compliance Notes

- **GDPR Compliance**: User data encryption, audit logging
- **API Key Management**: Environment variables only, never in code
- **Session Security**: Flask-Login with proper timeouts
- **Input Validation**: Both client and server-side validation
- **Rate Limiting**: Built into service classes to prevent API abuse