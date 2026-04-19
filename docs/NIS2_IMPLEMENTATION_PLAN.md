# NIS2 Compliance Platform — Детальный план реализации

> Версия: 1.0 | Дата: 19.04.2026
> Платформа: Andrii-IT NIS2 Compliance Platform (расширение vat-bot-1)

---

## Содержание

1. [Архитектура платформы](#1-архитектура-платформы)
2. [Модуль 1: BSI-Registrierungs-Assistent (Приоритет 7 → неделя 1-2)](#2-модуль-1-bsi-registrierungs-assistent)
3. [Модуль 2: Continuous Compliance Monitoring (Приоритет 6 → неделя 2-4)](#3-модуль-2-continuous-compliance-monitoring)
4. [Модуль 3: ISMS-Dokumenten-Generator (Приоритет 1 → неделя 3-8)](#4-модуль-3-isms-dokumenten-generator)
5. [Модуль 4: Geschäftsleitungs-Schulung (Приоритет 2 → неделя 7-12)](#5-модуль-4-geschäftsleitungs-schulung)
6. [Модуль 5: Incident Response Toolkit (Приоритет 4 → неделя 9-12)](#6-модуль-5-incident-response-toolkit)
7. [Модуль 6: Supply Chain Security (Приоритет 5 → неделя 7-10)](#7-модуль-6-supply-chain-security)
8. [Модуль 7: Mitarbeiter Awareness & Phishing-Simulation (Приоритет 3 → неделя 11-18)](#8-модуль-7-mitarbeiter-awareness--phishing-simulation)
9. [Единый NIS2 Dashboard](#9-единый-nis2-dashboard)
10. [Модель подписки и биллинг](#10-модель-подписки-и-биллинг)
11. [База данных — миграции](#11-база-данных--миграции)
12. [Деплой и инфраструктура](#12-деплой-и-инфраструктура)

---

## 1. Архитектура платформы

### 1.1 Текущее состояние проекта

Уже реализовано в vat-bot-1:

| Модуль | Путь | Покрытие NIS2 |
|--------|------|---------------|
| Pentesting / Security Scanner | `app/pentesting/` | §30 Nr. 5 — Schwachstellenmanagement |
| Compliance Checker | `compliance_checker/` | Юридическая compliance сайтов |
| TeamGuard | `app/teamguard/` | §30 Nr. 9 — IAM, Offboarding, Phishing Tests (базово) |
| MailGuard | `app/mailguard/` | §30 Nr. 2, 8, 10 — Email Security |
| VAT/Counterparty Verification | `crm/`, `services/` | §30 Nr. 4 — Supply Chain (частично) |
| CRM Monitoring | `crm/monitor.py`, `crm/monitoring_scheduler.py` | Continuous Monitoring (контрагенты) |
| Phone Intelligence | `routes/phoneintel.py` | Дополнительная верификация |

### 1.2 Целевая архитектура — новые модули

```
app/
├── nis2/                          # ← НОВЫЙ: NIS2 Compliance Hub
│   ├── __init__.py                # Blueprint registration
│   ├── models.py                  # Все NIS2-модели
│   ├── dashboard.py               # Единый NIS2 Dashboard
│   │
│   ├── bsi_registration/          # Модуль 1: BSI-Registrierung
│   │   ├── __init__.py
│   │   ├── routes.py              # Wizard-формы, API
│   │   └── generator.py           # Генерация данных для MUK-Portal
│   │
│   ├── continuous_monitoring/     # Модуль 2: Continuous Monitoring
│   │   ├── __init__.py
│   │   ├── routes.py              # Dashboard, настройки
│   │   ├── scanner.py             # Переиспользование pentesting scanner
│   │   └── scheduler.py           # APScheduler — ежемесячные сканы
│   │
│   ├── isms_docs/                 # Модуль 3: ISMS Document Generator
│   │   ├── __init__.py
│   │   ├── routes.py              # Интервью-wizard, загрузка документов
│   │   ├── interview.py           # AI-интервью (Claude API)
│   │   ├── generator.py           # DOCX/PDF генерация
│   │   └── templates_data/        # Шаблоны BSI 200-1/200-2/200-3
│   │       ├── risk_analysis.json
│   │       ├── security_policy.json
│   │       ├── incident_response_plan.json
│   │       ├── bcm_plan.json
│   │       ├── access_control.json
│   │       └── crypto_concept.json
│   │
│   ├── executive_training/        # Модуль 4: GF-Schulung
│   │   ├── __init__.py
│   │   ├── routes.py              # E-Learning страницы, сертификаты
│   │   ├── content.py             # Генерация контента модулей
│   │   └── certificate.py         # PDF-генерация Teilnahmezertifikat
│   │
│   ├── incident_response/         # Модуль 5: Incident Response
│   │   ├── __init__.py
│   │   ├── routes.py              # Формы, timeline, exports
│   │   ├── bsi_draft.py           # AI-генерация BSI Meldungen
│   │   └── playbooks.py           # IRP шаблоны по NIST SP 800-61
│   │
│   ├── supply_chain/              # Модуль 6: Supply Chain Security
│   │   ├── __init__.py
│   │   ├── routes.py              # Импорт, dashboard, отчёты
│   │   ├── scanner.py             # Лайт-скан сайтов поставщиков
│   │   └── avv_tracker.py         # AVV-документы, напоминания
│   │
│   └── awareness/                 # Модуль 7: Mitarbeiter Awareness
│       ├── __init__.py
│       ├── routes.py              # Модули обучения, результаты
│       ├── content_generator.py   # AI-генерация уроков
│       ├── phishing_engine.py     # Расширение TeamGuard phishing
│       └── reporting.py           # Квартальные отчёты
│
templates/
│   └── nis2/                      # Шаблоны для всех NIS2-модулей
│       ├── dashboard.html         # Единый NIS2 Dashboard
│       ├── bsi_registration/
│       ├── continuous_monitoring/
│       ├── isms_docs/
│       ├── executive_training/
│       ├── incident_response/
│       ├── supply_chain/
│       └── awareness/
│
static/
│   ├── js/nis2/                   # JavaScript для NIS2-модулей
│   └── css/nis2/                  # Стили NIS2-модулей
```

### 1.3 Принципы реализации

1. **Единый Blueprint** `nis2_bp` с sub-prefixes для каждого модуля
2. **Общая модель данных** в `app/nis2/models.py` — все таблицы с prefix `nis2_`
3. **Переиспользование** существующего кода:
   - `WebsiteSecurityScanner` из `app/pentesting/` → Continuous Monitoring + Supply Chain
   - `TeamGuard` → база для Awareness + Phishing
   - `MailGuard SMTP` → Phishing-Simulation delivery
   - CRM Monitoring Scheduler pattern → все scheduler задачи
4. **AI через Claude API** (Anthropic) — уже подключен, модель `claude-sonnet-4-6`
5. **Документы**: python-docx (DOCX) + WeasyPrint или reportlab (PDF)

---

## 2. Модуль 1: BSI-Registrierungs-Assistent

> **Цель**: Step-by-step wizard для регистрации в BSI через MUK-Portal
> **Срок**: Неделя 1-2 | **Сложность**: Низкая | **Доход**: €199 одноразово (lead magnet)

### 2.1 Функциональные требования

- [ ] Wizard из 5 шагов с прогресс-баром
- [ ] Проверка Betroffenheit (18 секторов, пороги 50 сотрудников / €10M оборота)
- [ ] Pre-fill данных из VAT-Verifizierung (если клиент уже на платформе)
- [ ] Генерация всех полей для MUK-Portal в JSON/CSV формате
- [ ] PDF-инструкция с скриншотами MUK-Portal + пошаговым описанием
- [ ] Чеклист требуемых документов (ELSTER-Zertifikat, Kontaktdaten, etc.)
- [ ] Email-уведомление с результатами

### 2.2 Wizard шаги

```
Шаг 1: Unternehmensdaten
  - Firmenname, Rechtsform (GmbH/AG/UG/etc.)
  - Handelsregisternummer + Registergericht
  - USt-IdNr (VIES-валидация через существующий сервис)
  - Anschrift (Straße, PLZ, Ort)
  - Mitarbeiterzahl, Jahresumsatz

Шаг 2: Sektor-Zuordnung
  - Auswahl из 18 секторов (Energie, Transport, Bankwesen, etc.)
  - Untersektor-Zuordnung
  - Автоматическое определение: besonders wichtige / wichtige Einrichtung
  - Информация о применимых штрафах

Шаг 3: Kontaktpersonen
  - Geschäftsführer (Name, Email, Telefon)
  - IT-Sicherheitsbeauftragter (Name, Email, Telefon)
  - Meldestelle (24/7 Erreichbarkeit)

Шаг 4: Technische Angaben
  - IP-Adressen-Bereiche
  - Domains
  - Verwendete IT-Dienste
  - Cloud-Anbieter

Шаг 5: Zusammenfassung & Export
  - Alle Daten in Übersicht
  - Export als PDF-Bericht
  - JSON-Export (для pre-fill в MUK-Portal)
  - Checkliste offener Aufgaben
```

### 2.3 Модель данных

```python
class BSIRegistration(db.Model):
    """BSI-MUK-Portal Registrierungsdaten."""
    __tablename__ = 'nis2_bsi_registrations'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)

    # Unternehmensdaten
    company_name = db.Column(db.String(300), nullable=False)
    legal_form = db.Column(db.String(50))        # GmbH, AG, UG, etc.
    hrb_number = db.Column(db.String(50))         # Handelsregisternummer
    registry_court = db.Column(db.String(100))    # Registergericht
    vat_id = db.Column(db.String(20))
    street = db.Column(db.String(200))
    postal_code = db.Column(db.String(10))
    city = db.Column(db.String(100))
    employee_count = db.Column(db.Integer)
    annual_revenue_eur = db.Column(db.BigInteger)

    # Sektor
    sector = db.Column(db.String(100))            # Energie, Transport, etc.
    subsector = db.Column(db.String(100))
    entity_type = db.Column(db.String(50))        # besonders_wichtig / wichtig

    # Kontaktpersonen (JSON)
    contacts_json = db.Column(db.Text)            # JSON: {gf: {}, it_security: {}, meldestelle: {}}

    # Technische Angaben (JSON)
    technical_json = db.Column(db.Text)           # JSON: {ip_ranges: [], domains: [], cloud: []}

    # Status
    wizard_step = db.Column(db.Integer, default=1)
    is_complete = db.Column(db.Boolean, default=False)
    exported_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2.4 Роуты

```python
# app/nis2/bsi_registration/routes.py
@nis2_bp.route('/bsi-registration/')                          # Landing page
@nis2_bp.route('/bsi-registration/check')                     # Betroffenheits-Check (бесплатно, без авторизации)
@nis2_bp.route('/bsi-registration/wizard/<int:step>', methods=['GET', 'POST'])  # Wizard steps 1-5
@nis2_bp.route('/bsi-registration/export/pdf')                # PDF export
@nis2_bp.route('/bsi-registration/export/json')               # JSON export
```

### 2.5 Маркетинговый Landing

- URL: `/nis2/bsi-registration/check` — **БЕЗ авторизации**
- Пользователь проверяет свою Betroffenheit бесплатно
- Результат: "Sie sind betroffen / Sie sind wahrscheinlich nicht betroffen"
- CTA: "Jetzt registrieren und Bußgelder vermeiden" → registration wall

### 2.6 Файлы для создания

```
app/nis2/__init__.py
app/nis2/models.py
app/nis2/dashboard.py
app/nis2/bsi_registration/__init__.py
app/nis2/bsi_registration/routes.py
app/nis2/bsi_registration/generator.py
templates/nis2/bsi_registration/landing.html
templates/nis2/bsi_registration/check.html
templates/nis2/bsi_registration/wizard_step1.html
templates/nis2/bsi_registration/wizard_step2.html
templates/nis2/bsi_registration/wizard_step3.html
templates/nis2/bsi_registration/wizard_step4.html
templates/nis2/bsi_registration/wizard_step5.html
templates/nis2/bsi_registration/export.html
static/js/nis2/bsi_wizard.js
```

### 2.7 Зависимости

```
# Уже есть:
# - Flask, SQLAlchemy, Flask-Login
# Добавить:
python-docx>=0.8.11    # DOCX генерация
weasyprint>=60.0        # PDF генерация (или reportlab)
```

---

## 3. Модуль 2: Continuous Compliance Monitoring

> **Цель**: Автоматический ежемесячный пересkан + тренды + алерты
> **Срок**: Неделя 2-4 | **Сложность**: Низкая | **Доход**: €99-199/мес

### 3.1 Функциональные требования

- [ ] Настройка targets (домены/поддомены) для мониторинга
- [ ] Ежемесячный автоматический scan через `WebsiteSecurityScanner`
- [ ] Хранение истории сканов → трендовый dashboard
- [ ] Email-алерты при деградации (new vulnerability, expired cert, etc.)
- [ ] Квартальный PDF-отчёт для руководства (автогенерация)
- [ ] Сравнение scan vs. scan (diff view)

### 3.2 Переиспользование кода

```python
# Из app/pentesting/security_scanner.py — уже есть:
from app.pentesting.security_scanner import WebsiteSecurityScanner

# Из crm/monitoring_scheduler.py — паттерн APScheduler:
# Аналогичный подход для NIS2 scheduler
```

### 3.3 Модель данных

```python
class MonitoringTarget(db.Model):
    """Домен/IP для постоянного мониторинга."""
    __tablename__ = 'nis2_monitoring_targets'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    scan_frequency = db.Column(db.String(20), default='monthly')  # weekly, monthly, quarterly
    last_scan_at = db.Column(db.DateTime)
    last_score = db.Column(db.Float)               # 0-100
    previous_score = db.Column(db.Float)            # предыдущий скан для diff
    alert_on_degradation = db.Column(db.Boolean, default=True)
    alert_email = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scans = db.relationship('MonitoringScan', backref='target', lazy='dynamic',
                            cascade='all, delete-orphan')


class MonitoringScan(db.Model):
    """Результат одного скана."""
    __tablename__ = 'nis2_monitoring_scans'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}nis2_monitoring_targets.id'), nullable=False)
    scan_type = db.Column(db.String(20), default='full')  # full, quick, headers_only
    score = db.Column(db.Float)                     # 0-100
    results_json = db.Column(db.Text)               # Полный результат скана (JSON)
    findings_count = db.Column(db.Integer, default=0)
    critical_count = db.Column(db.Integer, default=0)
    high_count = db.Column(db.Integer, default=0)
    medium_count = db.Column(db.Integer, default=0)
    low_count = db.Column(db.Integer, default=0)
    diff_json = db.Column(db.Text)                  # Diff с предыдущим сканом
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.4 Scheduler

```python
# app/nis2/continuous_monitoring/scheduler.py
def init_nis2_monitoring_scheduler(app):
    """Ежедневная проверка — какие targets нужно просканировать сегодня."""
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _run_scheduled_scans,
        trigger=CronTrigger(hour=2, minute=0),  # 02:00 ежедневно
        args=[app],
        id='nis2_continuous_monitoring',
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    return scheduler

def _run_scheduled_scans(app):
    """Проверяет все активные targets и сканирует те, у которых пришло время."""
    with app.app_context():
        now = datetime.utcnow()
        targets = MonitoringTarget.query.filter_by(is_active=True).all()
        for target in targets:
            if _should_scan(target, now):
                _perform_scan(target)
                _check_degradation(target)
```

### 3.5 Роуты

```python
@nis2_bp.route('/monitoring/')                                     # Dashboard с графиками
@nis2_bp.route('/monitoring/targets', methods=['GET', 'POST'])     # CRUD targets
@nis2_bp.route('/monitoring/targets/<int:id>/scans')               # История сканов
@nis2_bp.route('/monitoring/targets/<int:id>/scan-now', methods=['POST'])  # Ручной скан
@nis2_bp.route('/monitoring/report/quarterly')                     # Квартальный PDF
@nis2_bp.route('/monitoring/api/trend/<int:target_id>')            # JSON для графиков
```

### 3.6 Файлы для создания

```
app/nis2/continuous_monitoring/__init__.py
app/nis2/continuous_monitoring/routes.py
app/nis2/continuous_monitoring/scanner.py
app/nis2/continuous_monitoring/scheduler.py
app/nis2/continuous_monitoring/reporting.py
templates/nis2/continuous_monitoring/dashboard.html
templates/nis2/continuous_monitoring/targets.html
templates/nis2/continuous_monitoring/scan_history.html
templates/nis2/continuous_monitoring/scan_diff.html
static/js/nis2/monitoring_charts.js
```

---

## 4. Модуль 3: ISMS-Dokumenten-Generator

> **Цель**: AI-интервью → генерация ISMS-документов по BSI 200-1/200-2/200-3
> **Срок**: Неделя 3-8 | **Сложность**: Высокая | **Доход**: €500-1500 одноразово или €99/мес

### 4.1 Покрываемые документы (§30 BSIG)

| # | Документ | §30 Nr. | Формат |
|---|----------|---------|--------|
| 1 | IT-Sicherheitsleitlinie | Nr. 1 | DOCX + PDF |
| 2 | Risikoanalyse & Risikobewertung | Nr. 1 | DOCX + PDF |
| 3 | Incident Response Plan (IRP) | Nr. 2 | DOCX + PDF |
| 4 | Business Continuity Plan (BCP/DRP) | Nr. 3 | DOCX + PDF |
| 5 | Supply Chain Security Policy | Nr. 4 | DOCX + PDF |
| 6 | Schwachstellenmanagement-Konzept | Nr. 5 | DOCX + PDF |
| 7 | Kryptographie-Konzept | Nr. 8 | DOCX + PDF |
| 8 | Zugriffskontroll-Konzept | Nr. 9 | DOCX + PDF |
| 9 | MFA & Kommunikations-Policy | Nr. 10 | DOCX + PDF |
| 10 | Schulungskonzept | Nr. 7 | DOCX + PDF |

### 4.2 AI-Интервью Flow

```
Phase 1: Company Profile (5-7 минут)
  Q: Sektor und Unternehmensgröße?
  Q: Hauptgeschäftsprozesse?
  Q: IT-Infrastruktur (Cloud/On-Premise/Hybrid)?
  Q: Vorhandene Zertifizierungen (ISO 27001, etc.)?

Phase 2: IT-Landschaft (10-15 минут)
  Q: Wichtigste IT-Systeme und Anwendungen?
  Q: Netzwerk-Topologie (grob)?
  Q: Externe Dienstleister / Cloud-Services?
  Q: Datenkategorien (personenbezogen, geschäftskritisch)?

Phase 3: Bestehendes Sicherheitsniveau (10 минут)
  Q: Bestehende Sicherheitsmaßnahmen?
  Q: Backup-Strategie?
  Q: Zugriffskontrollsystem (AD, IAM)?
  Q: Incident-Management bisher?

Phase 4: Risikobewertung (10 минут)
  AI-gesteuert: Claude analysiert Antworten und fragt gezielt nach
  Q: Kritische Geschäftsprozesse und deren RTO/RPO?
  Q: Vergangene Sicherheitsvorfälle?
  Q: Größte identifizierte Risiken?

→ Output: Komplettes Dokumentenpaket in 45 Minuten statt 6 Monaten Beratung
```

### 4.3 Генератор документов

```python
# app/nis2/isms_docs/generator.py
class ISMSDocumentGenerator:
    """Генерирует ISMS-документы на основе AI-интервью."""

    DOCUMENTS = [
        'security_policy',          # IT-Sicherheitsleitlinie
        'risk_analysis',            # Risikoanalyse
        'incident_response_plan',   # IRP
        'business_continuity_plan', # BCP/DRP
        'supply_chain_policy',      # Lieferketten-Sicherheit
        'vulnerability_management', # Schwachstellenmanagement
        'crypto_concept',           # Kryptographie-Konzept
        'access_control',           # Zugriffskontroll-Konzept
        'mfa_communication',        # MFA & sichere Kommunikation
        'training_concept',         # Schulungskonzept
    ]

    def generate_all(self, interview_data: dict, user: User) -> list[GeneratedDocument]:
        """Генерирует все 10 документов на основе данных интервью."""
        documents = []
        for doc_type in self.DOCUMENTS:
            template = self._load_template(doc_type)
            prompt = self._build_prompt(template, interview_data)
            content = self._call_claude(prompt)
            docx_bytes = self._render_docx(content, doc_type, interview_data)
            documents.append(GeneratedDocument(
                doc_type=doc_type,
                content_md=content,
                docx_bytes=docx_bytes,
            ))
        return documents

    def _build_prompt(self, template: dict, interview_data: dict) -> str:
        """
        Строит промпт для Claude с:
        - Структурой документа из template
        - Ответами клиента из interview_data
        - BSI-стандартами как контекст
        """
        return f"""
        Du bist ein erfahrener ISMS-Berater und erstellst ein {template['title']}
        für ein Unternehmen mit folgenden Merkmalen:

        Unternehmen: {interview_data['company_profile']}
        Sektor: {interview_data['sector']}
        IT-Infrastruktur: {interview_data['it_landscape']}
        Bestehende Maßnahmen: {interview_data['existing_measures']}

        Erstelle das Dokument nach BSI-Standard {template['bsi_standard']}
        mit folgender Gliederung:
        {template['structure']}

        Anforderungen:
        - Professionelle Sprache (Deutsch, formal)
        - Konkrete, unternehmensspezifische Maßnahmen
        - Verantwortlichkeiten benennen
        - Zeitrahmen für Umsetzung
        - Revisionstermine festlegen
        """
```

### 4.4 Модель данных

```python
class ISMSInterview(db.Model):
    """AI-gesteuertes Interview zur ISMS-Dokumentenerstellung."""
    __tablename__ = 'nis2_isms_interviews'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)

    # Interview phases (JSON per phase)
    company_profile_json = db.Column(db.Text)
    it_landscape_json = db.Column(db.Text)
    security_level_json = db.Column(db.Text)
    risk_assessment_json = db.Column(db.Text)

    # Status
    current_phase = db.Column(db.Integer, default=1)  # 1-4
    is_complete = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = db.relationship('ISMSDocument', backref='interview', lazy='dynamic',
                                cascade='all, delete-orphan')


class ISMSDocument(db.Model):
    """Сгенерированный ISMS-документ."""
    __tablename__ = 'nis2_isms_documents'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}nis2_isms_interviews.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)

    doc_type = db.Column(db.String(50), nullable=False)  # security_policy, risk_analysis, etc.
    title = db.Column(db.String(300))
    content_md = db.Column(db.Text)                       # Markdown content
    version = db.Column(db.Integer, default=1)
    bsi_standard_ref = db.Column(db.String(50))           # BSI 200-1, 200-2, etc.
    nis2_paragraph_ref = db.Column(db.String(20))         # §30 Nr. X

    # File storage
    docx_stored = db.Column(db.Boolean, default=False)
    pdf_stored = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(500))                 # Path в cloud storage

    # Revision
    next_review_date = db.Column(db.Date)
    last_reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 4.5 Роуты

```python
@nis2_bp.route('/isms/')                                          # Обзор документов
@nis2_bp.route('/isms/interview/start', methods=['POST'])         # Начать интервью
@nis2_bp.route('/isms/interview/<int:id>/phase/<int:phase>', methods=['GET', 'POST'])
@nis2_bp.route('/isms/interview/<int:id>/generate', methods=['POST'])  # Генерация документов
@nis2_bp.route('/isms/documents/')                                # Список документов
@nis2_bp.route('/isms/documents/<int:id>')                        # Просмотр документа
@nis2_bp.route('/isms/documents/<int:id>/download/<fmt>')         # Скачать DOCX/PDF
@nis2_bp.route('/isms/documents/<int:id>/regenerate', methods=['POST'])  # Перегенерация
```

### 4.6 Файлы для создания

```
app/nis2/isms_docs/__init__.py
app/nis2/isms_docs/routes.py
app/nis2/isms_docs/interview.py
app/nis2/isms_docs/generator.py
app/nis2/isms_docs/templates_data/risk_analysis.json
app/nis2/isms_docs/templates_data/security_policy.json
app/nis2/isms_docs/templates_data/incident_response_plan.json
app/nis2/isms_docs/templates_data/bcm_plan.json
app/nis2/isms_docs/templates_data/access_control.json
app/nis2/isms_docs/templates_data/crypto_concept.json
app/nis2/isms_docs/templates_data/vulnerability_management.json
app/nis2/isms_docs/templates_data/supply_chain_policy.json
app/nis2/isms_docs/templates_data/mfa_communication.json
app/nis2/isms_docs/templates_data/training_concept.json
templates/nis2/isms_docs/overview.html
templates/nis2/isms_docs/interview_phase.html
templates/nis2/isms_docs/document_view.html
templates/nis2/isms_docs/document_list.html
```

### 4.7 Зависимости

```
python-docx>=0.8.11
anthropic>=0.25.0        # уже есть
weasyprint>=60.0         # PDF (альтернатива: reportlab)
markdown>=3.5            # MD → HTML для PDF
```

---

## 5. Модуль 4: Geschäftsleitungs-Schulung (§38 BSIG)

> **Цель**: E-Learning для Geschäftsführer с сертификатом
> **Срок**: Неделя 7-12 | **Сложность**: Средняя | **Доход**: €299-599/руководитель/год

### 5.1 Модули обучения

```
Modul 1: NIS2 — Was Geschäftsführer wissen müssen (15 Min)
  - Überblick NIS2UmsuCG
  - Persönliche Haftung §38 BSIG
  - Pflichten: Genehmigung, Überwachung, Schulung
  - Quiz: 10 Fragen

Modul 2: Risikomanagement für Entscheider (15 Min)
  - Schutzbedarfsfeststellung
  - Risikoanalyse verstehen
  - Kosten-Nutzen von Sicherheitsmaßnahmen
  - Quiz: 10 Fragen

Modul 3: Meldepflichten und Krisenmanagement (15 Min)
  - §32 BSIG: 3-stufiges Meldeverfahren
  - Wer meldet was wann?
  - Rolle der Geschäftsleitung im Krisenfall
  - Quiz: 10 Fragen

Modul 4: Lieferkettensicherheit (10 Min)
  - §30 Nr. 4 BSIG
  - Due Diligence auf Zulieferer
  - AVV-Management
  - Quiz: 8 Fragen

Modul 5: Cyberhygiene & aktuelle Bedrohungen (15 Min)
  - Top-10 Angriffsvektoren 2025/2026
  - Ransomware, Phishing, BEC — Was tun?
  - Sektorspezifische Risiken (AI-personalisiert)
  - Quiz: 10 Fragen

Modul 6: Prüfung & Zertifikat (20 Min)
  - Abschlusstest: 30 Fragen, 70% zum Bestehen
  - Teilnahmezertifikat mit:
    - Name, Datum, Inhaltsverzeichnis
    - Unique Zertifikat-ID (verifizierbar)
    - Gültig: 3 Jahre (§38 Auffrischungspflicht)
```

### 5.2 AI-Personalisierung

```python
# Каждый модуль персонализируется по:
# 1. Сектор клиента (Chemie → andere Beispiele als IT-Dienstleister)
# 2. Größe (50 MA → andere Maßnahmen als 500 MA)
# 3. Vorkenntnisse (Pre-Assessment-Quiz bestimmt Detailgrad)

def generate_module_content(module_id: int, user_profile: dict) -> dict:
    """Claude generiert sektorspezifische Beispiele und Szenarien."""
    prompt = f"""
    Erstelle den Inhalt für Schulungsmodul {module_id} für einen
    Geschäftsführer im Sektor {user_profile['sector']},
    Unternehmensgröße: {user_profile['employee_count']} Mitarbeiter.
    
    Format: JSON mit Feldern:
    - slides: [{{title, content_html, notes}}]
    - quiz: [{{question, options: [a,b,c,d], correct, explanation}}]
    """
```

### 5.3 Teilnahmezertifikat

```python
# app/nis2/executive_training/certificate.py
class CertificateGenerator:
    def generate(self, user: User, training_result: TrainingResult) -> bytes:
        """Генерирует PDF-сертификат с QR-кодом для верификации."""
        # Уникальный ID: NIS2-CERT-2026-XXXX
        cert_id = f"NIS2-CERT-{datetime.now().year}-{secrets.token_hex(4).upper()}"

        # QR-код → ссылка на верификацию: /nis2/certificates/verify/NIS2-CERT-...
        # PDF с corporate design
        # Срок: 3 года (§38 BSIG)
```

### 5.4 Модель данных

```python
class TrainingModule(db.Model):
    """Модуль обучения."""
    __tablename__ = 'nis2_training_modules'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    module_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer)
    content_json = db.Column(db.Text)             # Slides + Quiz
    target_audience = db.Column(db.String(50))    # executive, employee, it_admin
    is_active = db.Column(db.Boolean, default=True)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TrainingProgress(db.Model):
    """Прогресс пользователя по модулям."""
    __tablename__ = 'nis2_training_progress'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}nis2_training_modules.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    quiz_score = db.Column(db.Float)              # 0-100
    quiz_passed = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    time_spent_seconds = db.Column(db.Integer, default=0)


class TrainingCertificate(db.Model):
    """Сертификат о прохождении обучения."""
    __tablename__ = 'nis2_training_certificates'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)
    certificate_id = db.Column(db.String(30), unique=True, nullable=False)  # NIS2-CERT-2026-XXXX
    training_type = db.Column(db.String(50))      # executive, awareness
    modules_completed = db.Column(db.Text)        # JSON list of module IDs
    final_score = db.Column(db.Float)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.Date)              # +3 years
    pdf_path = db.Column(db.String(500))
    is_valid = db.Column(db.Boolean, default=True)
```

### 5.5 Роуты

```python
@nis2_bp.route('/training/')                                       # Обзор модулей
@nis2_bp.route('/training/executive/')                             # GF-Schulung Landing
@nis2_bp.route('/training/executive/module/<int:num>')             # Просмотр модуля
@nis2_bp.route('/training/executive/module/<int:num>/quiz', methods=['POST'])  # Quiz
@nis2_bp.route('/training/executive/exam', methods=['GET', 'POST'])  # Abschlussprüfung
@nis2_bp.route('/training/certificates/')                          # Мои сертификаты
@nis2_bp.route('/training/certificates/<cert_id>/download')        # PDF download
@nis2_bp.route('/nis2/certificates/verify/<cert_id>')              # Публичная верификация (без auth)
```

---

## 6. Модуль 5: Incident Response Toolkit (§32 BSIG)

> **Цель**: Веб-форма → AI генерирует BSI-Meldungen + IRP-чеклист
> **Срок**: Неделя 9-12 | **Сложность**: Средняя | **Доход**: €299-499/год подписка

### 6.1 Функциональные требования

- [ ] Incident Registration Form (свободный текст → структурированные данные)
- [ ] AI генерирует 3 черновика для BSI:
  - 24h Frühwarnung
  - 72h Zwischenmeldung
  - 1 Monat Abschlussbericht
- [ ] Чеклист действий по NIST SP 800-61:
  - Preparation → Detection → Containment → Eradication → Recovery → Lessons Learned
- [ ] Таймлайн инцидента с timestamps
- [ ] Audit-Log всех действий (для Nachweis)
- [ ] Export: PDF-отчёт + BSI-Format
- [ ] Опционально: DSGVO Art. 33 Meldetexte для DPA

### 6.2 BSI Meldungs-Generator

```python
# app/nis2/incident_response/bsi_draft.py
class BSIMeldungGenerator:
    """Генерирует черновики BSI-уведомлений по §32 BSIG."""

    STAGES = {
        'fruehwarnung': {
            'deadline_hours': 24,
            'title': 'Frühwarnung nach §32 Abs. 1 Nr. 1 BSIG',
            'required_fields': [
                'Verdacht auf Art des Vorfalls',
                'Vermutete Ursache (inkl. grenzüberschreitend)',
                'Betroffene Einrichtung',
                'Kontaktdaten Meldestelle',
            ]
        },
        'zwischenmeldung': {
            'deadline_hours': 72,
            'title': 'Zwischenmeldung nach §32 Abs. 1 Nr. 2 BSIG',
            'required_fields': [
                'Erste Bewertung des Vorfalls',
                'Schweregrad und Auswirkungen',
                'Kompromittierungsindikatoren (IoC)',
                'Ergriffene Gegenmaßnahmen',
            ]
        },
        'abschlussbericht': {
            'deadline_days': 30,
            'title': 'Abschlussbericht nach §32 Abs. 1 Nr. 4 BSIG',
            'required_fields': [
                'Ausführliche Beschreibung des Vorfalls',
                'Art der Bedrohung / Grundursache',
                'Ergriffene Abhilfemaßnahmen',
                'Grenzüberschreitende Auswirkungen',
                'Lessons Learned',
            ]
        }
    }

    def generate_draft(self, stage: str, incident_data: dict) -> str:
        """Claude generiert Meldungstext basierend auf Incident-Beschreibung."""
        stage_info = self.STAGES[stage]
        prompt = f"""
        Erstelle eine {stage_info['title']} für folgendes IT-Sicherheitsvorfall:

        Beschreibung: {incident_data['description']}
        Betroffene Systeme: {incident_data.get('affected_systems', 'nicht bekannt')}
        Zeitpunkt der Entdeckung: {incident_data.get('detected_at', 'nicht bekannt')}
        Ergriffene Sofortmaßnahmen: {incident_data.get('immediate_actions', 'keine')}

        Die Meldung MUSS folgende Pflichtfelder enthalten:
        {chr(10).join('- ' + f for f in stage_info['required_fields'])}

        Format: Professionelles Deutsch, BSI-konform, faktenbasiert.
        Keine Spekulationen — bei unbekannten Fakten "derzeit in Klärung" schreiben.
        """
        return self._call_claude(prompt)
```

### 6.3 Модель данных

```python
class Incident(db.Model):
    """IT-Sicherheitsvorfall."""
    __tablename__ = 'nis2_incidents'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)
    incident_id = db.Column(db.String(30), unique=True)  # INC-2026-XXXX

    # Incident details
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20))           # critical, high, medium, low
    status = db.Column(db.String(20), default='open')  # open, contained, eradicated, recovered, closed
    category = db.Column(db.String(50))           # ransomware, phishing, data_breach, dos, etc.

    # Timeline
    detected_at = db.Column(db.DateTime, nullable=False)
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    contained_at = db.Column(db.DateTime)
    eradicated_at = db.Column(db.DateTime)
    recovered_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    # Affected systems (JSON)
    affected_systems_json = db.Column(db.Text)
    affected_data_categories = db.Column(db.Text)  # JSON: ["personenbezogen", "geschaeftskritisch"]

    # BSI Meldungen
    fruehwarnung_deadline = db.Column(db.DateTime)    # detected_at + 24h
    zwischenmeldung_deadline = db.Column(db.DateTime) # detected_at + 72h
    abschlussbericht_deadline = db.Column(db.DateTime)# detected_at + 30 days
    fruehwarnung_sent = db.Column(db.Boolean, default=False)
    zwischenmeldung_sent = db.Column(db.Boolean, default=False)
    abschlussbericht_sent = db.Column(db.Boolean, default=False)

    # DSGVO
    dsgvo_relevant = db.Column(db.Boolean, default=False)
    dpa_notification_sent = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    drafts = db.relationship('IncidentDraft', backref='incident', lazy='dynamic',
                             cascade='all, delete-orphan')
    timeline_entries = db.relationship('IncidentTimeline', backref='incident', lazy='dynamic',
                                       cascade='all, delete-orphan')


class IncidentDraft(db.Model):
    """Черновик BSI-Meldung."""
    __tablename__ = 'nis2_incident_drafts'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}nis2_incidents.id'), nullable=False)
    stage = db.Column(db.String(30), nullable=False)  # fruehwarnung, zwischenmeldung, abschlussbericht
    content = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    is_approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.String(200))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IncidentTimeline(db.Model):
    """Audit-Log für Incident."""
    __tablename__ = 'nis2_incident_timeline'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}nis2_incidents.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # created, status_changed, draft_generated, etc.
    details = db.Column(db.Text)
    performed_by = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

### 6.4 Роуты

```python
@nis2_bp.route('/incidents/')                                      # Список инцидентов
@nis2_bp.route('/incidents/new', methods=['GET', 'POST'])          # Регистрация инцидента
@nis2_bp.route('/incidents/<int:id>')                              # Детали + таймлайн
@nis2_bp.route('/incidents/<int:id>/status', methods=['POST'])     # Обновление статуса
@nis2_bp.route('/incidents/<int:id>/generate/<stage>', methods=['POST'])  # AI-генерация мeldung
@nis2_bp.route('/incidents/<int:id>/drafts/<int:draft_id>')        # Просмотр/редактирование
@nis2_bp.route('/incidents/<int:id>/drafts/<int:draft_id>/approve', methods=['POST'])
@nis2_bp.route('/incidents/<int:id>/export/pdf')                   # Export
@nis2_bp.route('/incidents/<int:id>/checklist')                    # NIST SP 800-61 чеклист
```

---

## 7. Модуль 6: Supply Chain Security (§30 Nr. 4)

> **Цель**: Расширение vat-verifizierung для NIS2 supply chain requirements
> **Срок**: Неделя 7-10 | **Сложность**: Низкая-Средняя | **Доход**: €149-299/мес

### 7.1 Функциональные требования

- [ ] CSV/Excel импорт списка поставщиков
- [ ] Автоматическая VIES + Handelsregister + Sanctions проверка каждого
- [ ] Лайт-скан веб-сайтов поставщиков (headers, TLS, DNS — через `WebsiteSecurityScanner`)
- [ ] AVV-Tracker (Auftragsverarbeitungsvertrag):
  - Есть ли AVV? Когда подписан? Когда последний review?
  - Напоминания о просроченных AVV
- [ ] Sicherheitsbewertung каждого поставщика:
  - ISO 27001? SOC 2? BSI IT-Grundschutz?
  - TLS/Security score их сайта
  - Санкции? Ликвидирована?
- [ ] Ежеквартальный Supply Chain Risk Report (DOCX автогенерация)
- [ ] Dashboard: Top-10 riskiest suppliers, trend over time

### 7.2 Переиспользование существующего кода

```python
# Уже есть:
from services.vies import VIESService                    # VAT validation
from services.business_registry import BusinessRegistry  # DE/CZ/PL registries
from services.sanctions import SanctionsChecker          # EU/OFAC/UK
from services.enrichment_flow import EnrichmentOrchestrator  # Комбо-запрос
from app.pentesting.security_scanner import WebsiteSecurityScanner  # Security scan

# Supply Chain = orchestration этих сервисов + AVV-tracking + reporting
```

### 7.3 Модель данных

```python
class Supplier(db.Model):
    """Поставщик/контрагент в контексте NIS2 Supply Chain."""
    __tablename__ = 'nis2_suppliers'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id'), nullable=False)

    # Basic info
    company_name = db.Column(db.String(300), nullable=False)
    vat_id = db.Column(db.String(30))
    country = db.Column(db.String(5))
    domain = db.Column(db.String(255))
    contact_email = db.Column(db.String(200))
    category = db.Column(db.String(50))           # it_service, cloud, logistics, etc.
    criticality = db.Column(db.String(20))        # critical, high, medium, low

    # Verification results
    vies_valid = db.Column(db.Boolean)
    sanctions_clear = db.Column(db.Boolean)
    registry_active = db.Column(db.Boolean)
    last_verification_at = db.Column(db.DateTime)

    # Security assessment
    security_score = db.Column(db.Float)          # 0-100
    has_iso27001 = db.Column(db.Boolean)
    has_soc2 = db.Column(db.Boolean)
    has_bsi_grundschutz = db.Column(db.Boolean)
    tls_grade = db.Column(db.String(5))           # A+, A, B, C, F
    last_security_scan_at = db.Column(db.DateTime)

    # AVV tracking
    avv_exists = db.Column(db.Boolean, default=False)
    avv_signed_at = db.Column(db.Date)
    avv_review_due = db.Column(db.Date)
    avv_document_path = db.Column(db.String(500))

    # Risk score (computed)
    risk_score = db.Column(db.Float)              # 0-100 (higher = more risk)
    risk_factors_json = db.Column(db.Text)        # JSON: [{factor, score, description}]

    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assessments = db.relationship('SupplierAssessment', backref='supplier', lazy='dynamic',
                                  cascade='all, delete-orphan')


class SupplierAssessment(db.Model):
    """Snapshot проверки поставщика."""
    __tablename__ = 'nis2_supplier_assessments'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}nis2_suppliers.id'), nullable=False)
    assessment_type = db.Column(db.String(30))    # initial, quarterly, annual
    risk_score = db.Column(db.Float)
    findings_json = db.Column(db.Text)            # JSON: all findings
    assessed_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 7.4 Роуты

```python
@nis2_bp.route('/supply-chain/')                                   # Dashboard
@nis2_bp.route('/supply-chain/suppliers', methods=['GET', 'POST']) # CRUD
@nis2_bp.route('/supply-chain/suppliers/import', methods=['POST']) # CSV import
@nis2_bp.route('/supply-chain/suppliers/<int:id>')                 # Detail view
@nis2_bp.route('/supply-chain/suppliers/<int:id>/assess', methods=['POST'])  # Запустить оценку
@nis2_bp.route('/supply-chain/suppliers/<int:id>/avv', methods=['GET', 'POST'])  # AVV tracking
@nis2_bp.route('/supply-chain/report/quarterly')                   # Quarterly report PDF
@nis2_bp.route('/supply-chain/api/risk-overview')                  # JSON для dashboard
```

---

## 8. Модуль 7: Mitarbeiter Awareness & Phishing-Simulation

> **Цель**: §30 Nr. 7 — E-Learning для сотрудников + Phishing-Tests
> **Срок**: Неделя 11-18 | **Сложность**: Высокая | **Доход**: €3-5/сотрудник/мес

### 8.1 Переиспользование TeamGuard

TeamGuard (`app/teamguard/`) уже содержит:
- `TeamMember` model — управление сотрудниками
- `PhishingTest` + `PhishingClick` models — базовый phishing tracking
- `SecurityEvent` — аудит-лог
- Templates: `create_phishing_test.html`, `phishing_list.html`, `phishing_detail.html`

**Стратегия**: Расширить TeamGuard, а не создавать с нуля.

### 8.2 Новые компоненты

```python
# 1. Awareness-модули (12 в год = 1/месяц)
AWARENESS_MODULES = [
    {'month': 1,  'topic': 'Passwortsicherheit & MFA',         'duration': 10},
    {'month': 2,  'topic': 'Phishing erkennen',                'duration': 10},
    {'month': 3,  'topic': 'Social Engineering',               'duration': 10},
    {'month': 4,  'topic': 'Sicherer Umgang mit E-Mails',      'duration': 10},
    {'month': 5,  'topic': 'Mobile Sicherheit',                'duration': 10},
    {'month': 6,  'topic': 'Datenschutz am Arbeitsplatz',      'duration': 10},
    {'month': 7,  'topic': 'Ransomware — Was tun?',            'duration': 10},
    {'month': 8,  'topic': 'Sichere Nutzung von Cloud-Diensten','duration': 10},
    {'month': 9,  'topic': 'Physische Sicherheit & Clean Desk', 'duration': 10},
    {'month': 10, 'topic': 'Incident Reporting — Richtig melden','duration': 10},
    {'month': 11, 'topic': 'USB & externe Medien',             'duration': 10},
    {'month': 12, 'topic': 'Jahresrückblick & Wiederholung',   'duration': 15},
]

# 2. Phishing-Simulation Engine (расширение TeamGuard)
# - Шаблоны фишинговых писем (DE/EN)
# - SMTP-отправка через MailGuard infrastructure
# - Tracking: open, click, submit, report
# - Individuelles Nachschulungsmodul bei Klick

# 3. Reporting
# - Pro Mitarbeiter: Module completed, Quiz scores, Phishing clicks
# - Abteilungs-Dashboard
# - Quartalsbericht für GF (Nachweis §30 Nr. 7)
```

### 8.3 Phishing-Шаблоны

```python
PHISHING_TEMPLATES = [
    {
        'id': 'fake_invoice',
        'name': 'Gefälschte Rechnung',
        'difficulty': 'easy',
        'subject': 'Rechnung Nr. {invoice_nr} - Zahlung überfällig',
        'body_template': 'phishing/fake_invoice.html',
        'indicators': ['Dringlichkeit', 'Unbekannter Absender', 'Verdächtiger Link'],
    },
    {
        'id': 'password_reset',
        'name': 'Passwort-Reset',
        'difficulty': 'medium',
        'subject': 'Sicherheitswarnung: Passwort zurücksetzen erforderlich',
        'body_template': 'phishing/password_reset.html',
        'indicators': ['Generische Anrede', 'Zeitdruck', 'Verdächtige URL'],
    },
    {
        'id': 'ceo_fraud',
        'name': 'CEO-Fraud / BEC',
        'difficulty': 'hard',
        'subject': 'Vertraulich - Dringende Überweisung',
        'body_template': 'phishing/ceo_fraud.html',
        'indicators': ['Ungewöhnliche Anfrage', 'Vertraulichkeit', 'Zeitdruck'],
    },
    # ... 10+ шаблонов разной сложности
]
```

### 8.4 Роуты

```python
# Awareness Training
@nis2_bp.route('/awareness/')                                      # Dashboard
@nis2_bp.route('/awareness/modules/')                              # Список модулей
@nis2_bp.route('/awareness/modules/<int:id>')                      # Просмотр модуля
@nis2_bp.route('/awareness/modules/<int:id>/quiz', methods=['POST'])
@nis2_bp.route('/awareness/progress/<int:member_id>')              # Прогресс сотрудника

# Phishing Simulation (расширение TeamGuard)
@nis2_bp.route('/awareness/phishing/campaigns')                    # Список кампаний
@nis2_bp.route('/awareness/phishing/campaigns/new', methods=['GET', 'POST'])
@nis2_bp.route('/awareness/phishing/campaigns/<int:id>/results')
@nis2_bp.route('/awareness/phishing/track/<token>')                # Tracking pixel/link (без auth)

# Reporting
@nis2_bp.route('/awareness/reports/quarterly')                     # Quartalsbericht
@nis2_bp.route('/awareness/reports/individual/<int:member_id>')    # Per-person report
```

---

## 9. Единый NIS2 Dashboard

> **Цель**: Одна страница — полная картина NIS2-compliance

### 9.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  NIS2 Compliance Dashboard              Firma: Mustermann GmbH  │
│  ═══════════════════════════════════════════════════════════════  │
│                                                                  │
│  Gesamtstatus: ████████░░░░ 67%     [Maßnahmen: 6.5/10]         │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Nr.1 Risiko  │ │ Nr.2 Incident│ │ Nr.3 BCM     │             │
│  │ ✅ Erledigt  │ │ ⚠️ Teilweise │ │ ❌ Offen     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Nr.4 Supply  │ │ Nr.5 Vuln.   │ │ Nr.6 Audits  │             │
│  │ ⚠️ Teilweise │ │ ✅ Erledigt  │ │ ⚠️ Teilweise │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Nr.7 Schulung│ │ Nr.8 Krypto  │ │ Nr.9 IAM     │             │
│  │ ❌ Offen     │ │ ⚠️ Teilweise │ │ ❌ Offen     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐                                                │
│  │ Nr.10 MFA    │   Nächste Schritte:                            │
│  │ ❌ Offen     │   1. BCM-Dokument erstellen                    │
│  └──────────────┘   2. GF-Schulung abschließen                   │
│                      3. BSI-Registrierung prüfen                  │
│                                                                   │
│  ────────────────────────────────────────────────────────────── │
│  Quick Actions:                                                   │
│  [📋 ISMS Dokumente] [🔍 Security Scan] [🚨 Incident melden]    │
│  [📚 GF-Schulung]    [🔗 Supply Chain]  [👥 Awareness]           │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Compliance Score Berechnung

```python
# app/nis2/dashboard.py
def calculate_compliance_score(user_id: int) -> dict:
    """Рассчитывает NIS2-compliance score по 10 мерам §30."""
    scores = {}

    # Nr. 1: Risikoanalyse — есть ISMS-документы?
    isms_docs = ISMSDocument.query.filter_by(user_id=user_id).all()
    doc_types = {d.doc_type for d in isms_docs}
    scores['nr1_risk'] = {
        'score': min(100, len({'risk_analysis', 'security_policy'} & doc_types) * 50),
        'label': 'Risikoanalyse & IT-Sicherheit',
        'status': 'complete' if {'risk_analysis', 'security_policy'} <= doc_types else 'partial'
    }

    # Nr. 2: Incident Response — есть IRP документ + инструмент?
    has_irp = 'incident_response_plan' in doc_types
    scores['nr2_incident'] = {
        'score': 50 if has_irp else 0,
        'label': 'Sicherheitsvorfälle',
        'status': 'partial' if has_irp else 'open'
    }

    # Nr. 5: Schwachstellenmanagement — есть хоть один скан?
    has_scans = MonitoringScan.query.join(MonitoringTarget).filter(
        MonitoringTarget.user_id == user_id
    ).count() > 0
    scores['nr5_vuln'] = {
        'score': 100 if has_scans else 0,
        'label': 'Schwachstellenmanagement',
        'status': 'complete' if has_scans else 'open'
    }

    # Nr. 7: Schulung — GF + Mitarbeiter
    gf_cert = TrainingCertificate.query.filter_by(
        user_id=user_id, training_type='executive', is_valid=True
    ).first()
    scores['nr7_training'] = {
        'score': 50 if gf_cert else 0,
        'label': 'Schulungen & Awareness',
        'status': 'partial' if gf_cert else 'open'
    }

    # ... аналогично для остальных 6 мер

    total = sum(s['score'] for s in scores.values()) / len(scores)
    return {'measures': scores, 'total_score': total}
```

### 9.3 Роуты

```python
@nis2_bp.route('/')                                                # Главный NIS2 Dashboard
@nis2_bp.route('/api/compliance-score')                            # JSON для AJAX-обновления
```

---

## 10. Модель подписки и биллинг

### 10.1 NIS2-специфичные планы

```python
NIS2_PLANS = {
    'nis2_starter': {
        'name': 'NIS2 Starter',
        'price_monthly': 99,
        'price_yearly': 990,       # 2 месяца бесплатно
        'features': {
            'continuous_monitoring': True,    # 1 domain
            'monitoring_targets': 1,
            'security_scans': 12,            # 1/month
            'isms_documents': False,
            'executive_training': False,
            'incident_response': False,
            'supply_chain_suppliers': 0,
            'awareness_seats': 0,
            'quarterly_reports': True,
        }
    },
    'nis2_professional': {
        'name': 'NIS2 Professional',
        'price_monthly': 299,
        'price_yearly': 2990,
        'features': {
            'continuous_monitoring': True,    # 5 domains
            'monitoring_targets': 5,
            'security_scans': -1,            # unlimited
            'isms_documents': True,          # all 10
            'executive_training': True,      # 2 seats
            'executive_training_seats': 2,
            'incident_response': True,
            'supply_chain_suppliers': 20,
            'awareness_seats': 0,
            'quarterly_reports': True,
        }
    },
    'nis2_enterprise': {
        'name': 'NIS2 Enterprise',
        'price_monthly': 599,
        'price_yearly': 5990,
        'features': {
            'continuous_monitoring': True,    # unlimited
            'monitoring_targets': -1,
            'security_scans': -1,
            'isms_documents': True,
            'executive_training': True,      # 5 seats
            'executive_training_seats': 5,
            'incident_response': True,
            'supply_chain_suppliers': -1,    # unlimited
            'awareness_seats': -1,           # unlimited
            'quarterly_reports': True,
            'custom_ai_training': True,
        }
    }
}
```

### 10.2 Интеграция с существующей моделью Subscription

Расширить `auth/models.py` → `Subscription`:

```python
# Добавить в Subscription model:
nis2_plan = db.Column(db.String(30))  # nis2_starter, nis2_professional, nis2_enterprise
nis2_features_json = db.Column(db.Text)  # Cache of plan features
```

### 10.3 Stripe Products (создать в Stripe Dashboard)

```
Product: NIS2 Starter          → Price: €99/mo, €990/yr
Product: NIS2 Professional     → Price: €299/mo, €2990/yr
Product: NIS2 Enterprise       → Price: €599/mo, €5990/yr
Product: BSI-Registrierung     → Price: €199 one-time
Product: ISMS-Dokumentenpaket  → Price: €1500 one-time
Product: GF-Schulung (1 Sitz)  → Price: €499 one-time
```

---

## 11. База данных — миграции

### 11.1 Новые таблицы (13 таблиц)

```
nis2_bsi_registrations        # BSI-Registrierungs-Assistent
nis2_monitoring_targets       # Continuous Monitoring
nis2_monitoring_scans         # Continuous Monitoring
nis2_isms_interviews          # ISMS Document Generator
nis2_isms_documents           # ISMS Document Generator
nis2_training_modules         # GF-Schulung + Awareness
nis2_training_progress        # GF-Schulung + Awareness
nis2_training_certificates    # GF-Schulung + Awareness
nis2_incidents                # Incident Response
nis2_incident_drafts          # Incident Response
nis2_incident_timeline        # Incident Response
nis2_suppliers                # Supply Chain
nis2_supplier_assessments     # Supply Chain
```

### 11.2 Миграция

```bash
# Создание миграции
flask db migrate -m "Add NIS2 compliance platform tables"

# Применение
flask db upgrade
```

### 11.3 Порядок создания

```
Миграция 1 (Неделя 1): nis2_bsi_registrations
Миграция 2 (Неделя 2): nis2_monitoring_targets + nis2_monitoring_scans
Миграция 3 (Неделя 3): nis2_isms_interviews + nis2_isms_documents
Миграция 4 (Неделя 7): nis2_training_* (3 таблицы)
Миграция 5 (Неделя 7): nis2_suppliers + nis2_supplier_assessments
Миграция 6 (Неделя 9): nis2_incidents + nis2_incident_drafts + nis2_incident_timeline
```

---

## 12. Деплой и инфраструктура

### 12.1 Зависимости (requirements.txt additions)

```
python-docx>=0.8.11           # DOCX generation
weasyprint>=60.0              # PDF generation
qrcode>=7.4                   # QR codes for certificates
openpyxl>=3.1.0               # Excel import for supply chain
```

### 12.2 Environment Variables (новые)

```bash
# NIS2 Module
NIS2_ENABLED=true
NIS2_CLAUDE_MODEL=claude-sonnet-4-6

# Document Storage (Render disk or S3)
NIS2_DOCS_STORAGE=local          # local | s3
NIS2_DOCS_PATH=/data/nis2_docs   # for local
# AWS_S3_BUCKET=                  # for s3

# Certificates
NIS2_CERT_VERIFY_URL=https://vat-verifizierung.de/nis2/certificates/verify
```

### 12.3 Blueprint Registration (application.py)

```python
# В create_app():
try:
    from app.nis2 import nis2_bp
    app.register_blueprint(nis2_bp, url_prefix='/nis2')
except Exception as e:
    app.logger.warning('NIS2 blueprint not registered: %s', e)
```

### 12.4 Render.com Config

```yaml
# render.yaml — добавить disk для документов
services:
  - type: web
    name: vat-bot-1
    disk:
      name: nis2-docs
      mountPath: /data/nis2_docs
      sizeGB: 1
```

---

## Сводная таблица: Что, Когда, Сколько

| # | Модуль | Недели | Сложность | Файлы | Доход (прогноз) |
|---|--------|--------|-----------|-------|-----------------|
| 1 | BSI-Registrierung | 1-2 | Низкая | ~15 | €199/клиент (lead magnet) |
| 2 | Continuous Monitoring | 2-4 | Низкая | ~12 | €99-199/мес MRR |
| 3 | ISMS-Dokumente | 3-8 | Высокая | ~25 | €500-1500 one-shot + €99/мес |
| 4 | GF-Schulung | 7-12 | Средняя | ~18 | €299-599/руководитель/год |
| 5 | Incident Response | 9-12 | Средняя | ~15 | €299-499/год |
| 6 | Supply Chain | 7-10 | Средняя | ~14 | €149-299/мес |
| 7 | Awareness/Phishing | 11-18 | Высокая | ~20 | €3-5/сотрудник/мес |
| - | NIS2 Dashboard | 2-4 | Низкая | ~5 | (входит в подписку) |

**Итого новых файлов**: ~124
**Новых таблиц БД**: 13
**Срок до полной платформы**: 18 недель (4.5 месяца)
**Срок до первого MRR**: 4 недели (BSI-Reg + Continuous Monitoring)

---

## Дорожная карта (Timeline)

```
Неделя 1-2:   ████ BSI-Registrierung MVP
                    └─ Landing (бесплатный Betroffenheits-Check)
                    └─ Wizard 5 шагов
                    └─ PDF/JSON export
                    └─ Маркетинг: "61% der Unternehmen noch nicht registriert!"

Неделя 2-4:   ████ Continuous Monitoring MVP
                    └─ Target management
                    └─ Scheduler (monthly scans)
                    └─ Trend dashboard
                    └─ Email alerts
                    └─ → ПЕРВЫЙ MRR ПРОДУКТ

Неделя 3-8:   ██████████ ISMS-Dokumenten-Generator
                    └─ AI Interview (4 phases)
                    └─ 10 документов-шаблонов
                    └─ DOCX/PDF генерация
                    └─ → HIGH-TICKET PRODUCT

Неделя 7-10:  ████████ Supply Chain Security
                    └─ CSV import
                    └─ Auto-assessment (VIES+Sanctions+Security)
                    └─ AVV-Tracker
                    └─ → UPSELL vat-verifizierung клиентов

Неделя 7-12:  ████████████ GF-Schulung E-Learning
                    └─ 6 модулей + Abschlussprüfung
                    └─ Teilnahmezertifikat (PDF + QR)
                    └─ → RECURRING (3-year renewal)

Неделя 9-12:  ████████ Incident Response Toolkit
                    └─ Incident form
                    └─ AI BSI-Meldungen
                    └─ NIST Checklist
                    └─ → INSURANCE-LIKE PRODUCT

Неделя 11-18: ████████████████ Awareness + Phishing
                    └─ 12 monthly modules
                    └─ Phishing campaign engine
                    └─ Per-employee tracking
                    └─ → VOLUME PRODUCT (per seat)

Неделя 2-18:  ═══════════════════════ NIS2 Dashboard (iterativ)
                    └─ Compliance Score
                    └─ 10 Maßnahmen Status
                    └─ Next Steps / Quick Actions
```

---

## Следующий шаг

Для начала реализации BSI-Registrierungs-Assistent (неделя 1-2), нужно:

1. Создать `app/nis2/__init__.py` с Blueprint
2. Создать `app/nis2/models.py` с `BSIRegistration`
3. Создать роуты + шаблоны wizard
4. Добавить миграцию
5. Зарегистрировать blueprint в `application.py`

Скажи "go" — и начнём кодить первый модуль.
