# Counterparty Verification System + MailGuard - AI Development Guide

## Project Overview
Multi-module Flask SaaS platform combining:
1. **Counterparty Verification**: Automated EU business partner verification with VAT validation, sanctions checks, OSINT scans
2. **MailGuard**: Intelligent email processing system with AI-powered responses, security scanning, and multi-provider support (Gmail, Microsoft 365, IMAP)

## Architecture & Core Patterns

### Application Structure
```
├── wsgi.py               # Application entry point (resolves app/ directory conflict)
├── application.py        # Flask factory with all blueprint registrations
├── config.py             # Environment-based configuration classes
├── app/
│   ├── crm/models.py     # SQLAlchemy models (Company, Counterparty, VerificationCheck)
│   ├── auth/models.py    # User authentication & subscription models
│   ├── mailguard/        # MailGuard email intelligence module
│   │   ├── models.py     # Email models (MailAccount, MailMessage, MailRule, MailDraft)
│   │   ├── views.py      # Dashboard, account management, approval endpoints
│   │   ├── oauth.py      # Gmail & Microsoft OAuth 2.0 flows
│   │   ├── connectors/   # Email provider integrations
│   │   │   ├── gmail.py      # Gmail API client
│   │   │   ├── microsoft.py  # Microsoft Graph API client
│   │   │   ├── imap.py       # Universal IMAP client
│   │   │   └── smtp.py       # Universal SMTP sender
│   │   ├── rules.py      # Priority-based rule engine
│   │   ├── nlp_reply.py  # OpenAI GPT-4 reply generation
│   │   └── scanner.py    # Attachment security scanner
│   └── services/         # External API integrations
│       ├── vies.py          # EU VAT validation (SOAP API)
│       ├── handelsregister.py # German business register
│       ├── sanctions.py     # EU/OFAC/UK sanctions lists
│       └── osint/           # Open Source Intelligence scanner
└── templates/
    ├── mailguard/        # Email dashboard templates
    └── ...               # Other feature templates
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

#### 4. MailGuard Email Intelligence Pattern (`app/mailguard/`)
```python
# OAuth Flow Pattern
class GmailConnector:
    def authenticate(self, user_id: str) -> str:
        flow = OAuth2WebServerFlow(...)
        auth_url = flow.step1_get_authorize_url()
        return auth_url  # Redirect user to Google consent
    
    def callback(self, code: str) -> Dict[str, str]:
        credentials = flow.step2_exchange(code)
        encrypted_token = encrypt(credentials.to_json())
        return {'access_token': encrypted_token}

# Rule Engine Pattern
class RuleEngine:
    def process_message(self, message: MailMessage) -> MailDraft:
        rules = MailRule.query.filter_by(is_enabled=True)\
            .order_by(MailRule.priority.desc()).all()
        for rule in rules:
            if rule.matches(message):
                return self.apply_rule(rule, message)

# AI Reply Generation Pattern
class NLPReplyGenerator:
    def generate_reply(self, message: str, context: Dict) -> str:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional business assistant..."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
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
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vat_bot_dev
DB_SCHEMA=vat_verification
SECRET_KEY=your-secret-key
# API keys for external services...

# 4. Database initialization
flask db upgrade

# 5. Start development server
flask run --debug
```

### Database Schema Management
- **Models**: `crm/models.py` (Company, Counterparty, VerificationCheck, CheckResult)
- **Migrations**: Use `flask db migrate/upgrade` for schema changes
- **Multi-tenant**: PostgreSQL schemas for production isolation
- **Relationships**: User → VerificationCheck → CheckResult (cascading deletes)

### MailGuard Database Models (`app/mailguard/models.py`)
```python
# Core models with relationships
MailAccount:     # User email accounts (Gmail, Microsoft, IMAP)
  - user_id → User
  - provider (gmail|microsoft|imap)
  - email, encrypted_access_token, encrypted_refresh_token
  - is_active, last_sync_at

MailMessage:     # Incoming emails
  - account_id → MailAccount
  - counterparty_id → KnownCounterparty (optional)
  - provider_msg_id (unique), thread_id
  - from_email, to_email, subject, body_text, body_html
  - received_at, is_read, priority

MailRule:        # Processing rules
  - name, is_enabled, priority (0-100)
  - match_from, match_domain, match_subject_regex
  - action (auto_reply|draft|quarantine|ignore)
  - requires_human (Boolean)
  - workhours_json (JSON string)

MailDraft:       # AI-generated replies
  - message_id → MailMessage
  - body, generated_by_ai (Boolean)
  - approved_by_user (Boolean), sent_at
  - confidence_score (0.0-1.0)

KnownCounterparty:  # Trusted contacts
  - email, name, company, trust_level (low|medium|high)
  - auto_reply_enabled, notes

ScanReport:      # Security scans
  - draft_id → MailDraft
  - scan_type (antivirus|phishing|spam)
  - result (clean|suspicious|malicious), details_json
```

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

---

## MailGuard - Email Intelligence Module

### Current Implementation Status (October 2025)

**✅ Completed Features:**
- Database models: 6 tables (MailAccount, MailMessage, MailRule, MailDraft, KnownCounterparty, ScanReport)
- Blueprint architecture: `app/mailguard/` with views, models, oauth
- Dashboard UI: Stats overview, accounts table, rules management, pending approvals
- Connector framework: Gmail, Microsoft Graph, IMAP, SMTP clients (implemented but not integrated)
- AI reply generation: OpenAI GPT-4 integration (`nlp_reply.py`)
- Rule engine: Priority-based matching system (`rules.py`)
- Security scanner: Attachment analysis framework (`scanner.py`)

**⚠️ Partially Implemented:**
- OAuth flows: Code exists but routes are placeholders
- Email connectors: Classes implemented but not connected to dashboard
- Background processing: APScheduler configured but no tasks running

**❌ Not Yet Implemented:**
- OAuth callback endpoints (Gmail, Microsoft)
- IMAP account setup form
- Email fetching/syncing background tasks
- AI reply approval workflow (backend ready, UI needs work)
- Rule creation/editing forms
- Attachment security scanning integration

### MailGuard Routes (`app/mailguard/views.py`)

**Working Routes:**
```python
@mailguard_bp.route('/')                              # Dashboard with stats
@mailguard_bp.route('/accounts')                      # Account management page
@mailguard_bp.route('/rules')                         # Rules management page
@mailguard_bp.route('/counterparties')                # Trusted contacts page
@mailguard_bp.route('/approve/<int:draft_id>')        # Approve draft reply
@mailguard_bp.route('/reject/<int:draft_id>')         # Reject draft reply
@mailguard_bp.route('/api/accounts')                  # List accounts (JSON)
@mailguard_bp.route('/api/drafts/pending')            # Pending approvals (JSON)
@mailguard_bp.route('/webhook/gmail')                 # Gmail push notifications
@mailguard_bp.route('/webhook/outlook')               # Outlook push notifications
```

**Placeholder Routes (Need Implementation):**
- `/auth/gmail` - Initiate Gmail OAuth flow
- `/auth/gmail/callback` - Handle Gmail OAuth callback
- `/auth/microsoft` - Initiate Microsoft OAuth flow
- `/auth/microsoft/callback` - Handle Microsoft OAuth callback
- `/accounts/add-imap` - IMAP account setup form
- `/accounts/<id>` - Account details and settings
- `/rules/create` - Rule creation form
- `/rules/<id>/edit` - Rule editing form
- `/messages` - Email inbox view
- `/messages/<id>` - Email thread view

### MailGuard Key Technologies

**Installed Dependencies:**
```
cryptography==41.0.7              # Token encryption (Fernet)
google-api-python-client==2.108.0 # Gmail API
google-auth==2.23.4               # Google OAuth
google-auth-oauthlib==1.1.0       # OAuth helpers
google-auth-httplib2==0.1.1       # HTTP transport
msal==1.25.0                      # Microsoft Authentication Library
apscheduler==3.10.4               # Background job scheduling
imapclient==2.3.1                 # IMAP protocol client
openai==1.12.0                    # GPT-4 for AI replies
```

**Environment Variables Required:**
```bash
# Gmail OAuth (Google Cloud Console)
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxx

# Microsoft OAuth (Azure App Registration)
MS_CLIENT_ID=xxx
MS_CLIENT_SECRET=xxx
MS_TENANT_ID=common  # or specific tenant

# OpenAI API
OPENAI_API_KEY=sk-xxx

# Token Encryption
MAILGUARD_ENCRYPTION_KEY=xxx  # 32-byte Fernet key

# Optional: External file scanner API
FILE_SCANNER_URL=https://api.virustotal.com/v3/files
FILE_SCANNER_API_KEY=xxx
```

---

## Development Roadmap & Paid API Integration Plans

### Phase 1: MailGuard OAuth Integration (Next Priority)
**Goal:** Enable users to connect Gmail and Microsoft 365 accounts

**Tasks:**
1. Implement Gmail OAuth flow:
   - Create `/auth/gmail` endpoint to initiate OAuth
   - Create `/auth/gmail/callback` to handle authorization code
   - Store encrypted tokens in `MailAccount`
   - Test Gmail API connection (fetch 1 email)

2. Implement Microsoft OAuth flow:
   - Create `/auth/microsoft` endpoint with MSAL library
   - Create `/auth/microsoft/callback` to exchange code
   - Store encrypted tokens in `MailAccount`
   - Test Microsoft Graph API (fetch 1 email)

3. Implement IMAP account setup:
   - Create form at `/accounts/add-imap`
   - Validate IMAP credentials with test connection
   - Store encrypted credentials in `MailAccount`
   - Test IMAP connection with IMAPClient

**Paid APIs Needed:**
- ✅ OpenAI GPT-4 API (already integrated) - ~$0.03 per AI reply
- 🆓 Gmail API (free with quotas)
- 🆓 Microsoft Graph API (free with quotas)

---

### Phase 2: Email Syncing & Background Processing
**Goal:** Automatically fetch and process incoming emails

**Tasks:**
1. Create background email fetcher:
   - APScheduler job every 5 minutes
   - Fetch new emails from all active `MailAccount`s
   - Parse email content (text, HTML, attachments)
   - Create `MailMessage` records

2. Implement rule engine integration:
   - Match incoming `MailMessage` against `MailRule`s
   - Generate AI replies for matched emails
   - Create `MailDraft` records requiring approval

3. Add email sending capability:
   - Send approved drafts via SMTP
   - Update `MailDraft.sent_at` timestamp
   - Mark original `MailMessage` as replied

**Paid APIs Needed:**
- ✅ OpenAI GPT-4 (already covered)
- 🆓 Gmail/Microsoft Graph for sending (free)

---

### Phase 3: Enhanced Verification with Paid APIs
**Goal:** Upgrade counterparty verification with premium data sources

**Current Free Sources:**
- VIES (EU VAT validation) - Free but limited data
- Handelsregister (German) - Free but slow scraping
- OFAC/EU sanctions lists - Free but manual parsing
- OSINT tools (WHOIS, DNS, SSL) - Free but shallow

**Planned Paid API Integrations:**

#### 3.1 Company Data Enrichment
```python
# service: ClearbitAPI (https://clearbit.com)
# cost: $99-$999/month
# features: Company profiles, employee count, funding, social media

class ClearbitService:
    def enrich_company(self, domain: str) -> Dict:
        response = requests.get(
            f'https://company.clearbit.com/v2/companies/find?domain={domain}',
            headers={'Authorization': f'Bearer {CLEARBIT_API_KEY}'}
        )
        return {
            'name': response['name'],
            'employees': response['metrics']['employees'],
            'funding': response['metrics']['raised'],
            'linkedin': response['linkedin']['handle']
        }
```

**Alternative:** OpenCorporates API ($150/month) - Global company registry

#### 3.2 Advanced Sanctions & Risk Screening
```python
# service: Dow Jones Risk & Compliance (https://risk.dowjones.com)
# cost: Custom pricing (~$500-2000/month)
# features: Real-time sanctions, PEP lists, adverse media, 200+ watchlists

class DowJonesRiskService:
    def screen_entity(self, name: str, country: str) -> Dict:
        payload = {
            'name': name,
            'country_codes': [country],
            'category': 'person,organization'
        }
        response = requests.post(
            'https://api.dowjones.com/risk/entities/v1/match',
            headers={'Authorization': f'Bearer {DJ_API_KEY}'},
            json=payload
        )
        return {
            'risk_score': response['match_score'],
            'sanctioned': response['has_sanctions'],
            'pep': response['is_pep'],
            'adverse_media': response['adverse_media_count']
        }
```

**Alternative:** ComplyAdvantage API ($200-1000/month) - Sanctions/PEP screening

#### 3.3 Financial Credit Checks
```python
# service: Creditsafe API (https://www.creditsafe.com)
# cost: ~€0.50-2.00 per report
# features: Credit scores, payment behavior, financial statements

class CreditsafeService:
    def get_credit_report(self, company_id: str, country: str) -> Dict:
        response = requests.get(
            f'https://connect.creditsafe.com/v1/companies/{country}/{company_id}',
            headers={'Authorization': f'Bearer {CREDITSAFE_TOKEN}'}
        )
        return {
            'credit_score': response['report']['creditScore']['value'],
            'credit_limit': response['report']['creditLimit']['value'],
            'payment_behavior': response['report']['paymentData']['dbt']
        }
```

**Alternative:** Dun & Bradstreet API - Global business credit reports

#### 3.4 Enhanced OSINT Intelligence
```python
# service: SecurityTrails API (https://securitytrails.com)
# cost: $99-599/month
# features: Historical DNS, WHOIS, SSL certificate history, subdomain discovery

class SecurityTrailsService:
    def deep_scan(self, domain: str) -> Dict:
        response = requests.get(
            f'https://api.securitytrails.com/v1/domain/{domain}',
            headers={'APIKEY': SECURITYTRAILS_KEY}
        )
        return {
            'dns_history': response['current_dns'],
            'subdomains': response['subdomains'],
            'whois_history': response['whois'],
            'ssl_certificates': response['ssl_certificates']
        }
```

#### 3.5 Email Security & Verification
```python
# service: Hunter.io API (https://hunter.io)
# cost: $49-399/month
# features: Email verification, company email patterns, deliverability checks

class HunterService:
    def verify_email(self, email: str) -> Dict:
        response = requests.get(
            f'https://api.hunter.io/v2/email-verifier?email={email}',
            params={'api_key': HUNTER_API_KEY}
        )
        return {
            'deliverable': response['data']['status'] == 'valid',
            'score': response['data']['score'],
            'smtp_check': response['data']['smtp_check']
        }
```

**For MailGuard Attachment Scanning:**
```python
# service: VirusTotal API (https://www.virustotal.com)
# cost: Free tier 500 req/day, Premium $600+/month
# features: 70+ antivirus engines, URL/file scanning, malware analysis

class VirusTotalService:
    def scan_attachment(self, file_hash: str) -> Dict:
        response = requests.get(
            f'https://www.virustotal.com/api/v3/files/{file_hash}',
            headers={'x-apikey': VIRUSTOTAL_KEY}
        )
        return {
            'malicious': response['data']['attributes']['last_analysis_stats']['malicious'],
            'suspicious': response['data']['attributes']['last_analysis_stats']['suspicious'],
            'reputation': response['data']['attributes']['reputation']
        }
```

---

### Phase 4: Subscription Tier Integration
**Goal:** Monetize premium API features with tiered access

**Proposed Subscription Plans:**

1. **Free Tier** (Current):
   - 5 verifications/month
   - Basic VIES + OSINT
   - MailGuard: 1 email account, manual replies only

2. **Starter** (€29/month):
   - 50 verifications/month
   - Basic APIs + OpenCorporates
   - MailGuard: 3 email accounts, AI replies with approval

3. **Professional** (€99/month):
   - 500 verifications/month
   - All APIs including Creditsafe, Hunter.io
   - MailGuard: 10 email accounts, auto-replies, rule engine

4. **Enterprise** (€299/month):
   - Unlimited verifications
   - Premium APIs (Dow Jones Risk, Clearbit)
   - MailGuard: Unlimited accounts, custom AI training
   - Dedicated support

**Implementation in `auth/models.py`:**
```python
class Subscription:
    api_tier = db.Column(db.String(20))  # 'free', 'starter', 'pro', 'enterprise'
    
    def can_use_premium_api(self, api_name: str) -> bool:
        tier_apis = {
            'free': ['vies', 'osint'],
            'starter': ['vies', 'osint', 'opencorporates', 'hunter'],
            'pro': ['creditsafe', 'securitytrails', 'virustotal'],
            'enterprise': ['dowjones', 'clearbit', 'dun_bradstreet']
        }
        return api_name in tier_apis.get(self.api_tier, [])
```

---

### Phase 5: AI-Powered Insights & Automation
**Goal:** Use machine learning to improve verification and email handling

**Planned Features:**

1. **Risk Scoring Model:**
   - Train on historical verification data
   - Predict counterparty risk (0-100 score)
   - Flag high-risk patterns automatically

2. **Email Intent Classification:**
   - Categorize emails (invoice, inquiry, complaint, spam)
   - Route to appropriate workflows
   - Auto-archive low-priority emails

3. **Custom AI Reply Training:**
   - Fine-tune GPT-4 on company communication style
   - Learn from approved/rejected drafts
   - Personalize replies per counterparty

4. **Anomaly Detection:**
   - Detect unusual payment requests
   - Flag suspicious email patterns
   - Alert on domain impersonation

**Paid AI Services:**
- OpenAI GPT-4 API (already integrated)
- OpenAI Fine-tuning ($0.08/1K tokens)
- Azure ML for custom models (if needed)

---

## Implementation Priority Order

**Next 2 Weeks:**
1. ✅ MailGuard OAuth flows (Gmail + Microsoft)
2. ✅ IMAP account setup form
3. ✅ Email fetching background job

**Next Month:**
4. 🔄 Rule engine activation
5. 🔄 AI reply approval workflow
6. 🔄 Email sending integration

**Next Quarter:**
7. 💰 Integrate 2-3 paid APIs (Creditsafe, Hunter.io, SecurityTrails)
8. 💰 Create subscription tier logic
9. 💰 Update UI with premium feature badges

**Long-term (6 months+):**
10. 🤖 ML risk scoring model
11. 🤖 Email intent classification
12. 🤖 Custom AI training per user

---

## Critical Notes for AI Assistant

### MailGuard Naming Conventions
- Model field: `is_enabled` (not `is_active`) in `MailRule`
- Model field: `is_active` in `MailAccount`
- Always check model definitions before writing queries

### Current Dashboard State
- URL: https://vat-bot-1.onrender.com/mailguard/
- Status: ✅ Renders successfully with empty data
- Button actions: Show alerts (temporary placeholders)
- Next step: Implement OAuth callback routes

### Deployment
- Entry point: `wsgi.py` (not `app.py` due to directory conflict)
- Command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
- Database: PostgreSQL on Render.com
- Migrations: Run `flask db upgrade` in Render shell

### Testing Paid APIs
- Start with free tiers/trials
- Use sandbox environments when available
- Implement rate limiting and caching
- Log all API calls for cost tracking

---

*Last Updated: October 27, 2025*
*MailGuard Status: Dashboard deployed, OAuth integration pending*
*Premium API Integration: Planning phase*