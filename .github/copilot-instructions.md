# Counterparty Verification System - Development Guide

## Project Overview
Flask веб-додаток для автоматизованої перевірки контрагентів через інтеграцію з офіційними реєстрами та API. Система приймає дані компанії та контрагента, перевіряє їх через різні джерела (VIES, Handelsregister, санкційні списки) і надає комплексну оцінку надійності.

## Architecture & Core Structure

### Directory Structure
```
project_root/
├── app.py                    # Flask application entry point
├── config.py                 # API keys, configuration management  
├── .env                      # Environment variables (API keys, DB configs)
├── requirements.txt          # Python dependencies
├── static/                   # CSS/JS assets for 3-column UI
├── templates/                # Jinja2 templates for web interface
├── services/                 # API integration modules
│   ├── vies.py              # EU VAT validation service
│   ├── handelsregister.py   # German business register
│   ├── sanctions.py         # EU/OFAC/UK sanctions lists
│   ├── insolvency.py        # Insolvenzbekanntmachungen.de
│   └── opencorporates.py    # Global business registry
├── crm/                     # Database and CRM integration
│   ├── models.py            # SQLAlchemy models (companies, checks, results)
│   ├── save_results.py      # Result persistence logic
│   └── monitor.py           # Daily monitoring and change detection
└── notifications/           # Alert system (Email/Telegram)
```

### Key Components
- **Web Interface**: 3-column layout (company data, counterparty data, verification results)
- **API Services**: Individual modules for each data source with unified response format
- **Database Layer**: Companies, verification checks, results history, alerts
- **Monitoring System**: Daily re-checks with change notifications
- **CRM Integration**: Results storage and historical tracking

## Data Sources & API Integrations

### Primary Verification Sources
- **VIES** (`services/vies.py`): EU VAT number validation
- **Handelsregister** (`services/handelsregister.py`): German company registration data
- **Sanctions Lists** (`services/sanctions.py`): EU/OFAC/UK consolidated checks
- **Insolvency** (`services/insolvency.py`): German bankruptcy announcements
- **OpenCorporates** (`services/opencorporates.py`): Global business registry

### API Integration Patterns
```python
# Standard service response format
{
    "status": "valid|warning|error",
    "source": "vies|handelsregister|sanctions",
    "data": {...},
    "last_checked": "2025-10-02T10:30:00Z",
    "confidence": 0.95
}
```

### Error Handling Strategy
- Implement retry logic with exponential backoff for API failures
- Cache successful responses to reduce API call frequency
- Graceful degradation when services are unavailable
- Log all API requests/responses for debugging and compliance

## Database Schema

### Core Models (`crm/models.py`)
```python
class Company(db.Model):
    # Requester company data (left column)
    vat_number, legal_address, company_name, email, phone

class Counterparty(db.Model):
    # Target verification company (middle column)  
    vat_number, company_name, address, email, domain, country

class VerificationCheck(db.Model):
    # Individual verification session
    company_id, counterparty_id, check_date, overall_status

class CheckResult(db.Model):
    # Results from each service
    check_id, service_name, status, data_json, confidence_score
```

## Development Workflows

### Flask Application Structure
- Use Flask blueprints for organizing routes (main, api, admin)
- Implement form validation using WTForms for data input
- Use SQLAlchemy with PostgreSQL for production, SQLite for development
- Configure Flask-Migrate for database schema management

### Service Integration Development
```python
# Template for new service integration
async def check_service(company_data):
    try:
        response = await api_call(company_data)
        return format_standard_response(response)
    except APIException as e:
        return error_response(e)
```

### Testing Strategy
- Unit tests for each service module with mocked API responses
- Integration tests for database operations and Flask routes
- End-to-end tests for complete verification workflows
- Mock external APIs in test environment to avoid rate limits

## Configuration Management

### Environment Variables (`.env`)
```
FLASK_ENV=development|production
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=flask_secret_key

# API Keys
VIES_API_KEY=
HANDELSREGISTER_API_KEY=
OPENCORPORATES_API_KEY=
SANCTIONS_API_KEY=

# Notifications
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_SERVER=
SMTP_USERNAME=
SMTP_PASSWORD=
```

### Configuration Patterns
- Store sensitive API keys in environment variables only
- Use different config classes for development/staging/production
- Implement API rate limiting configuration per service
- Configure monitoring intervals and notification thresholds

## User Interface Guidelines

### 3-Column Layout Structure
1. **Left Column**: Company data input (requester information)
2. **Middle Column**: Counterparty data input (verification target)
3. **Right Column**: Verification results with status indicators

### Status Indicators
- ✅ **Valid**: All checks passed successfully
- ⚠️ **Warning**: Minor issues or incomplete data
- ❌ **Problem**: Critical issues or sanctions found

### Form Validation Rules
- VAT numbers: validate format per country before API calls
- Email addresses: validate format and check domain existence
- Company names: normalize and trim whitespace
- Addresses: validate required fields per jurisdiction

## Monitoring & Notifications

### Daily Monitoring (`crm/monitor.py`)
```python
# Re-check all active counterparties daily
# Compare results with previous checks
# Trigger notifications for status changes
# Update confidence scores based on data freshness
```

### Notification Triggers
- New sanctions list matches
- Insolvency proceedings started
- VAT number validity changes
- Significant confidence score drops

## Performance Optimization

### Caching Strategy
- Redis cache for API responses (TTL: 24 hours for most services)
- Database query optimization with proper indexing
- Async API calls for parallel service checks
- Background job processing with Celery for monitoring

### API Rate Limiting
- Implement backoff strategies for each service
- Queue API requests to avoid hitting rate limits
- Cache negative results to prevent repeated failed calls
- Monitor API usage and costs per service

## Security & Compliance

### Data Protection
- Encrypt sensitive company data at rest
- Implement audit logging for all verification activities
- Secure API key storage and rotation procedures
- GDPR compliance for storing counterparty data

### Access Control
- Role-based access for different user types
- API authentication for programmatic access
- Session management with proper timeouts
- Input sanitization to prevent injection attacks

## Development Commands

### Local Development Setup
```bash
pip install -r requirements.txt
flask db init                 # Initialize database
flask db migrate             # Create migration
flask db upgrade            # Apply migrations
flask run --debug          # Start development server
```

### Testing Commands
```bash
pytest tests/              # Run unit tests
pytest tests/integration/ # Run integration tests
flask test-apis           # Test all external API connections
```

### Production Deployment
```bash
gunicorn app:app          # Production WSGI server
celery -A app.celery worker # Background task processing
celery beat               # Scheduled monitoring tasks
```

## API Integration Checklist
- [ ] Implement standard response format for all services
- [ ] Add comprehensive error handling and logging  
- [ ] Configure appropriate caching and rate limiting
- [ ] Add monitoring for API health and response times
- [ ] Document API costs and usage limits
- [ ] Implement fallback strategies for service outages