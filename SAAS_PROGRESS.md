# VAT Verifizierung - SaaS Platform

## Projektstatus: Enrichment Orchestrator Implemented (Phase 1-4 abgeschlossen, Phase 5 in Progress)

### 🎯 Projektziel
Multi-Modul SaaS-Plattform kombiniert:
1. **Counterparty Verification**: Automatisierte EU-Geschäftspartner-Überprüfung mit VAT-Validierung, Sanktionsprüfungen, OSINT-Scans
2. **Enrichment Orchestrator** 🆕: Intelligentes Auto-Fill-System kombiniert VIES + Business Registries + OSINT für automatische Formular-Vervollständigung
3. **MailGuard**: Intelligentes E-Mail-Verarbeitungssystem mit KI-gestützten Antworten, Sicherheitsprüfungen und Multi-Provider-Unterstützung (Gmail, Microsoft 365, IMAP)
4. **CRM & Monitoring**: Kontrahenten-Management mit täglichen Statusüberwachungen
5. **Subscription Management**: Stripe-basierte Abonnements mit automatischer Abrechnung

---

## ✅ Was wurde implementiert (FREE TIER KOMPLETT)

### 1. **Enrichment Orchestrator** 🆕 ✅ (November 2025)
- **EnrichmentOrchestrator Class** (`services/enrichment_flow.py`):
  - Kombiniert 3 Datenquellen: VIES + Business Registries + OSINT
  - Intelligentes Fallback-System (wenn VAT fehlt → OSINT, wenn Domain fehlt → Registry)
  - Unterstützt Input: `vat_number`, `email`, `domain`, `company_name`, `country_code_hint`
- **API Integration** (`application.py`):
  - Bestehender `/api/vat-lookup` Endpoint modernisiert
  - Verwendet `EnrichmentOrchestrator` statt nur `VatLookupService`
  - Backward compatible mit Frontend
- **Datenquellen** (alle FREE):
  - **VIES API**: VAT-Validierung mit Firmennamen und Adresse
  - **OSINT Scanner**: WHOIS (Organisation, Land, Stadt), DNS, SSL, HTTP Headers
  - **Business Registries**: DE/CZ/PL Handelsregister-Daten
- **Frontend Integration** (`static/js/app.js`):
  - VAT-Input blur event → automatischer API-Call
  - Auto-Fill mit visueller Hervorhebung (3.5s gelber Hintergrund)
  - `field.dataset.autofilled` tracking für User-Edit-Erkennung
- **Response Format**:
  ```json
  {
    "success": true,
    "prefill": { /* 10+ Felder */ },
    "services": { /* Raw API Responses */ },
    "messages": [ /* User-friendly Statusmeldungen */ ]
  }
  ```
- **Dokumentation**: `ENRICHMENT_GUIDE.md` (35 Seiten komplett)

### 2. **Authentifizierung & Benutzerverwaltung** ✅
- **Flask-Login Integration**: Vollständige Session-Verwaltung
- **User Model** (`auth/models.py`): Email-Bestätigung, Passwort-Hashing, Abonnement-Tracking
- **Registrierung/Login/Logout**: Deutsche UI mit E-Mail-Validierung
- **Passwort-Reset**: Token-basiert mit itsdangerous
- **Admin User Creation**: `create_admin.py` Skript (admin@example.com / admin123)

### 2. **Subscription System** ✅
- **Subscription Model**: Plan-Management (Free/Starter/Professional/Enterprise)
- **API-Quota-System**: 
  - Free: 5 Verifications/Monat
  - Starter: 50/Monat (€29)
  - Professional: 500/Monat (€99)
  - Enterprise: Unbegrenzt (€299)
- **Payment Model**: Stripe-Transaktionshistorie
- **Quota Enforcement**: Middleware-basierte Limitierung (`can_perform_verification()`)

### 3. **Stripe Integration** ✅
- **Checkout Sessions**: `POST /payments/create-checkout-session`
- **Webhook Handler**: `POST /payments/webhook` (7 Events verarbeitet)
  - `checkout.session.completed` → Aktivierung
  - `invoice.payment_succeeded` → Quota-Reset
  - `customer.subscription.deleted` → Downgrade zu Free
  - Weitere: updated, created, payment_failed
- **Price IDs**: In `config.py` konfiguriert
- **Signature Verification**: HMAC mit STRIPE_WEBHOOK_SECRET

### 4. **Counterparty Verification (Free Services)** ✅
- **VIES API Integration** (`services/vies.py`): EU VAT-Validierung (SOAP API)
- **Handelsregister Scraper** (`services/handelsregister.py`): Deutsche Firmenregister
- **Sanctions Checks** (`services/sanctions.py`): EU/OFAC/UK Sanktionslisten
- **Result Persistence** (`crm/save_results.py`): Speicherung in `verification_checks` + `check_results`
- **3-Column UI**: Company Data → Counterparty Data → Results (German interface)

### 5. **OSINT Scanner** ✅
- **OSINT Models** (`crm/osint_models.py`): OsintScan, OsintFinding
- **Scanner Modules** (`services/osint/`):
  - WHOIS Adapter (Domain-Registrierungsdaten)
  - DNS Adapter (A, AAAA, MX, NS, TXT Records)
  - SSL Labs Adapter (Zertifikatsprüfung, Bewertung)
  - Security Headers Adapter (HTTP-Sicherheitsheader)
  - Robots.txt Crawler
  - Social Media Link Detector
- **OSINT Dashboard**: `/osint` (Scanhistorie, neue Scans)
- **Integration**: Automatische OSINT-Prüfung bei Kontrahenten-Verifizierung

### 6. **CRM & Monitoring** ✅
- **Models** (`crm/models.py`):
  - Company (Ihre Firmen)
  - Counterparty (Geschäftspartner)
  - VerificationCheck (Prüfungshistorie)
  - CheckResult (Detaillierte Ergebnisse)
  - Alert (Benachrichtigungen)
- **Monitoring Service** (`crm/monitor.py`):
  - `run_daily_checks()` → Tägliche Statusprüfungen
  - Change Detection: VAT-Status, Sanktionen, Insolvenz
  - Alert-Generierung (critical/high/medium/low)
- **CRM Dashboard**: `/crm/counterparties` (Liste, Details, Monitoring-Toggle)
- **API Endpoints**: `/api/counterparties/<id>/monitoring` (Aktivierung/Deaktivierung)

### 7. **MailGuard - Email Intelligence (Models & Core Logic)** ✅
- **Database Models** (`app/mailguard/models.py`):
  - MailAccount (Gmail/Microsoft/IMAP Konten, verschlüsselte Tokens)
  - MailMessage (Eingangsnachrichten, Risikobewertung)
  - MailRule (Priority-basierte Verarbeitungsregeln)
  - MailDraft (KI-generierte Antworten, Genehmigungsworkflow)
  - KnownCounterparty (Vertrauenswürdige Kontakte)
  - ScanReport (Sicherheitsprüfungen: Antivirus, Phishing, Spam)
- **Connectors** (`app/mailguard/connectors/`):
  - Gmail API Client (`gmail.py`) - OAuth 2.0 Flow
  - Microsoft Graph Client (`msgraph.py`) - MSAL Auth
  - IMAP Client (`imap.py`) - IMAPClient
  - SMTP Sender (`smtp.py`) - smtplib
- **AI Reply Generator** (`app/mailguard/nlp_reply.py`): OpenAI GPT-4 Integration
- **Rule Engine** (`app/mailguard/rules.py`): Priority-basiertes Matching
- **Security Scanner** (`app/mailguard/scanner.py`): Attachment-Analyse (VirusTotal API ready)
- **Dashboard**: `/mailguard` (Konten, Regeln, ausstehende Genehmigungen)

### 8. **Landing Page & UI** ✅
- **Marketing Page** (`templates/landing.html`): Deutsche Landingpage mit Preisübersicht
- **Features Section**: 6 Hauptfunktionen dargestellt
- **Pricing Tiers**: Free/Starter/Professional/Enterprise
- **FAQ Section**: Häufige Fragen
- **Legal Pages**: AGB (`/legal/agb`), Datenschutz (`/legal/datenschutz`), Impressum (`/legal/impressum`)

### 9. **Database & Migrations** ✅
- **PostgreSQL-First**: Keine SQLite-Unterstützung mehr
- **Schema Isolation**: `vat_verification` Schema für Multi-Tenancy
- **7 Alembic Migrations**: Idempotente, schema-aware Migrationen
  - 361def0cfaed: Initial models (users, companies, subscriptions)
  - cd954586ac25: OSINT tables
  - c8560cadc898: user_id backfill für Counterparties
  - f9b5e3a7c2d4: MailGuard tables
  - a1b2c3d4e5f6: Attachment metadata
  - 6d7e8f9a0b1c: OSINT indexes
  - 7b1be3569a24: MailRule reply instructions
- **Automatic Schema Creation**: `ensure_schema()` Hook in `application.py`

### 10. **Deployment** ✅
- **Render.com**: Produktions-Deployment (PostgreSQL)
- **Entry Point**: `wsgi.py` (löst app/ Directory-Konflikt)
- **Environment Variables**: 15+ ENV vars konfiguriert (.env Template)
- **Auto-Deploy**: GitHub Push → Render Build → Migrations → Server Start

---

## ⚠️ Teilweise implementiert (80% fertig)

### MailGuard OAuth Integration
- **Code existiert**: `app/mailguard/oauth.py` (Gmail + Microsoft OAuth Flows)
- **Nicht verbunden**: Routes `/auth/gmail`, `/auth/microsoft` sind Platzhalter
- **Fehlende Implementation**:
  - OAuth Callback-Handler (`/auth/gmail/callback`, `/auth/microsoft/callback`)
  - IMAP Account Setup Form (`/accounts/add-imap`)
  - Background Email Fetching (APScheduler Jobs nicht gestartet)
  - Email Sending Integration (SMTP/Gmail API senden)

### CRM-MailGuard Sync
- **KnownCounterparty existiert**: Separate Tabelle für MailGuard-Kontakte
- **Keine Synchronisation**: Kein Link zu `crm.Counterparty`
- **Benötigt**: Automatische Verknüpfung bei E-Mail-Erkennung

---

## 📋 Noch zu implementieren (PHASE 5: PAID APIS)

### Nächste Priorität: MailGuard OAuth Fertigstellung
1. **Gmail OAuth Flow**:
   - `GET /mailguard/auth/gmail` → Start OAuth (redirect zu Google Consent)
   - `GET /mailguard/auth/gmail/callback` → Code Exchange → Token-Speicherung
   - Test: 1 E-Mail abrufen via Gmail API

2. **Microsoft OAuth Flow**:
   - `GET /mailguard/auth/microsoft` → MSAL Flow starten
   - `GET /mailguard/auth/microsoft/callback` → Token-Austausch
   - Test: 1 E-Mail abrufen via Microsoft Graph

3. **IMAP Setup**:
   - Form bei `/mailguard/accounts/add-imap`
   - Validierung mit Test-Verbindung
   - Verschlüsselte Speicherung (Fernet)

4. **Background Email Fetching**:
   - APScheduler Job (alle 5 Minuten)
   - Fetch von allen aktiven `MailAccount`s
   - Parsing (text, HTML, attachments) → `MailMessage` erstellen

5. **Email Sending**:
   - Senden via SMTP/Gmail API/Microsoft Graph
   - `MailDraft.sent_at` Timestamp-Update
   - `MailMessage.replied` Flag setzen

### Premium API-Integration (Phase 5.2 - Bezahlt)

---

## 🏗️ Architektur-Übersicht

```
vat-bot-1/
├── app.py                      # Flask-Hauptanwendung
├── config.py                   # Konfiguration
├── requirements.txt            # Aktualisiert mit SaaS-Abhängigkeiten
│
├── auth/                       # ✅ NEU: Authentifizierungsmodul
│   ├── __init__.py
│   ├── models.py              # User, Subscription, Payment
│   └── forms.py               # Registrierungs-/Login-Formulare
│
├── crm/                        # Bestehende Datenbankmodelle
│   ├── models.py              # Company, Counterparty, VerificationCheck
│   ├── save_results.py
│   └── monitor.py
│
├── services/                   # API-Integrationen
│   ├── vies.py
│   ├── sanctions.py
│   └── handelsregister.py
│
├── templates/
│   ├── base.html              # ✅ Auf Deutsch übersetzt
│   ├── index.html             # ✅ Auf Deutsch übersetzt
│   ├── landing.html           # ✅ NEU: Marketing-Landingpage
│   ├── history.html
│   └── check_details.html
│
└── static/
    ├── css/
    │   ├── style.css
    │   └── landing.css        # ✅ NEU: Landing-Page-Stile
    └── js/
        ├── app.js
        └── translations.js    # ✅ NEU: Übersetzungs-Helper
```

---

## 🔑 Umgebungsvariablen

Neue benötigte Variablen in `.env`:

```env
# Bestehende Variablen
FLASK_ENV=development
DATABASE_URL=sqlite:///vat_verification.db
SECRET_KEY=your-secret-key

# NEU: Stripe-Konfiguration
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# NEU: E-Mail-Konfiguration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@vatverification.com

# NEU: Anwendungskonfiguration
APP_NAME="VAT Verifizierung"
SUPPORT_EMAIL=support@vatverification.com
```

---

## 🚀 Nächste Schritte

### Sofort:
1. **Authentifizierungsrouten vervollständigen**
   - Login/Register-Ansichten
   - E-Mail-Bestätigung
   - Passwort-Reset

2. **Datenbank migrieren**
   ```bash
   flask db migrate -m "Add user authentication and subscriptions"
   flask db upgrade
   ```

3. **Stripe-Testmodus einrichten**
   - Stripe-Konto erstellen
   - API-Schlüssel hinzufügen
   - Produkte konfigurieren

### Diese Woche:
4. **Benutzer-Dashboard erstellen**
5. **Admin-Panel implementieren**
6. **Zahlungsablauf testen**

### Nächster Monat:
7. **Produktionsbereitstellung**
8. **Marketing-Material erstellen**
9. **Beta-Launch**

---

## 📝 Hinweise

- Alle Benutzerkommunikation ist auf Deutsch
- Preise sind in EUR
- DSGVO-Konformität wird berücksichtigt
- Datenbanken werden in EU-Rechenzentren gehostet

---

**Stand: 2. Oktober 2025**  
**Status: Phase 1-3 abgeschlossen (60% Fortschritt)**
