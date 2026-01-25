# Counterparty Verification System + MailGuard

Flask SaaS platform for automated business partner verification and intelligent email processing. The system integrates with official registries (VIES, Handelsregister, sanctions lists) and provides AI-powered email management with security scanning.

## 🎯 Основні можливості

### Counterparty Verification
- **3-колонковий веб-інтерфейс**: Дані компанії → Дані контрагента → Результати перевірки
- **Автоматизовані перевірки**: VIES VAT, Handelsregister, санкційні списки EU/OFAC/UK
- **OSINT Scanner**: WHOIS, DNS, SSL Labs, Security Headers для digital due diligence
- **CRM Integration**: Збереження контрагентів з історією перевірок
- **Monitoring System**: Щоденні перевірки з алертами про зміни статусу

### Phone Intelligence (PhoneInfoga Integration)
- **Risk Assessment**: Carrier, line type (mobile/VoIP/virtual), disposable numbers
- **Scam Detection**: FTC Do Not Call complaints database (937+ US numbers), suspicious patterns
- **Privacy-First**: No personal identification, metadata-only analysis
- **Risk Scoring**: 0-100 score with low/medium/high verdicts
- **Optional Deep Scan**: PhoneInfoga CLI integration for enhanced signals

### MailGuard Email Intelligence
- **Multi-Provider Support**: Gmail (OAuth), Microsoft 365 (OAuth), IMAP
- **AI Reply Generation**: OpenAI GPT-4 для автоматичних відповідей
- **Security Scanning**: Аналіз вкладень, phishing detection, spam filtering
- **Rule Engine**: Priority-based автоматична обробка по відправнику/темі/домену
- **Approval Workflow**: Human-in-the-loop для критичних рішень

### SaaS Features
- **Authentication**: Flask-Login with email confirmation
- **Subscriptions**: Free (5 checks/month), Starter, Professional, Enterprise
- **Stripe Integration**: Automated billing with webhook handling
- **Multi-tenant**: PostgreSQL schema-based isolation

## 🏗️ Архітектура

```
├── wsgi.py                   # Application entry point (resolves app/ directory conflict)
├── application.py            # Flask factory with all blueprints
├── config.py                 # Environment-based configuration
├── requirements.txt          # Python dependencies
├── templates/                # Jinja2 templates (German UI)
├── static/                   # CSS/JS assets
├── services/                 # API integration modules
│   ├── vies.py              # EU VAT validation (SOAP API)
│   ├── handelsregister.py   # German business register scraper
│   ├── sanctions.py         # EU/OFAC/UK sanctions lists
│   └── osint/               # Open Source Intelligence scanner
├── crm/                     # CRM and verification database
│   ├── models.py            # Company, Counterparty, VerificationCheck
│   ├── osint_models.py      # OsintScan, OsintFinding
│   ├── save_results.py      # Result persistence logic
│   └── monitor.py           # Daily monitoring service
├── auth/                    # Authentication and subscriptions
│   ├── models.py            # User, Subscription, Payment
│   └── routes.py            # Login, register, password reset
├── app/mailguard/           # MailGuard email intelligence module
│   ├── models.py            # MailAccount, MailMessage, MailRule, MailDraft
│   ├── views.py             # Dashboard, account management
│   ├── oauth.py             # Gmail & Microsoft OAuth flows
│   ├── connectors/          # Gmail, Microsoft Graph, IMAP, SMTP clients
│   ├── nlp_reply.py         # OpenAI GPT-4 reply generation
│   └── scanner.py           # Attachment security scanner
└── migrations/              # Alembic database migrations (7 versions)
```

## � Privacy & Security Notes

- **Phone Intelligence**: The phone analysis feature uses only metadata (carrier, line type, risk patterns) and does not perform personal identification. Raw phone numbers are not stored or logged. Scam detection uses the public BlockGuard database (FTC Do Not Call complaints) with 937+ US phone numbers.
- **Data Retention**: Verification results are stored for user history but can be deleted on request.
- **GDPR Compliance**: All user data is encrypted and processed in accordance with EU privacy regulations.

## �🚀 Швидкий старт

### 1. Встановлення залежностей

```bash
# Клонування репозиторію
git clone <your-repo-url>
cd vat-bot-1

# Створення віртуального середовища
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Встановлення пакетів
pip install -r requirements.txt
```

### 2. Налаштування PostgreSQL бази даних

**Важливо**: Проект використовує PostgreSQL як основну базу даних (SQLite не підтримується).

```bash
# Переконайтеся, що PostgreSQL встановлено і запущено
# Для Windows: Перевірте службу "PostgreSQL" у Services

# Створіть базу даних (якщо вона не існує)
createdb -U postgres vat_bot_dev

# Або через psql:
psql -U postgres
CREATE DATABASE vat_bot_dev;
\q
```

**Примітка**: Якщо PostgreSQL працює на нестандартному порту (наприклад, 5433), оновіть `DATABASE_URL` у `.env`.

### 3. Налаштування конфігурації

Створіть файл `.env` у корені проекту:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database (PostgreSQL)
# ВАЖЛИВО: Перевірте ваш порт PostgreSQL (стандартно 5432, але може бути 5433)
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/vat_bot_dev
DB_SCHEMA=vat_verification

# API Keys (опціонально для тестування)
VIES_API_KEY=
HANDELSREGISTER_API_KEY=
OPENCORPORATES_API_KEY=
SANCTIONS_API_KEY=

# MailGuard OAuth (опціонально)
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
MS_CLIENT_ID=
MS_CLIENT_SECRET=

# OpenAI для MailGuard AI-відповідей
OPENAI_API_KEY=

# Notifications (опціонально)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_SERVER=
SMTP_USERNAME=
SMTP_PASSWORD=
```

### 4. Ініціалізація бази даних

```bash
# Застосування міграцій до PostgreSQL
flask db upgrade

# Перевірте, що всі міграції застосовано:
# Шукайте повідомлення: "Running upgrade ... -> 7b1be3569a24, Add reply instructions to MailRule"
```

### 5. Створення адміністративного користувача

```bash
# Запустіть скрипт створення адміна
python create_admin.py

# Отримаєте:
# Email: admin@example.com
# Password: admin123
# Plan: Free (5 checks/month)
```

⚠️ **Важливо**: Змініть пароль адміна після першого входу!

### 6. Запуск додатку

```bash
# Режим розробки з автоперезавантаженням
flask run --debug

# Або через Python
python wsgi.py
```

Відкрийте браузер і перейдіть на `http://localhost:5000`

**Авторизація**:
- Email: `admin@example.com`
- Password: `admin123`

## 🔧 Використання

### Основний робочий процес

1. **Введіть дані вашої компанії** (ліва колонка):
   - VAT номер (обов'язково)
   - Назва компанії
   - Юридична адреса
   - Контактні дані

2. **Введіть дані контрагента** (середня колонка):
   - Назва компанії (обов'язково)
   - Країна (обов'язково)
   - VAT номер (якщо є)
   - Адреса, домен, контакти

3. **Переглядайте результати** (права колонка):
   - Загальний статус: ✅ Валідно, ⚠️ Попередження, ❌ Проблема
   - Детальні результати по кожному сервісу
   - Рівень довіри (0-100%)

### Перевірені джерела даних

- **VIES**: Перевірка дійсності EU VAT номерів
- **Handelsregister**: Німецький комерційний реєстр
- **Sanctions**: Консолідовані санкційні списки EU/OFAC/UK

## 📊 Моніторинг та алерти

### Щоденний моніторинг

```bash
# Запуск моніторингу вручну
flask monitor-daily

# Або через Python
python -c "from crm.monitor import MonitoringService; MonitoringService().run_daily_monitoring()"
```

### Тестування API підключень

```bash
# Перевірка всіх API
flask test-apis

# Тестування нотифікацій
python -c "from notifications.alerts import NotificationService; NotificationService(app.config).test_notifications()"
```

## 🛠️ Розробка

### Додавання нового сервісу перевірки

1. Створіть новий файл в `services/your_service.py`:

```python
from typing import Dict
from datetime import datetime

class YourService:
    def check_company(self, company_data: dict) -> Dict:
        return {
            'status': 'valid|warning|error',
            'source': 'your_service',
            'data': {...},
            'last_checked': datetime.utcnow().isoformat(),
            'confidence': 0.95,
            'response_time_ms': 150,
            'error_message': None
        }
```

2. Інтегруйте в `app.py`:

```python
from services.your_service import YourService

def run_verification_services(counterparty_data):
    results = {}
    
    # Додайте ваш сервіс
    your_service = YourService()
    results['your_service'] = your_service.check_company(counterparty_data)
    
    return results
```

### Структура бази даних

```sql
-- Основні таблиці
companies              # Дані компанії-заявника
counterparties         # Дані контрагентів
verification_checks    # Сесії перевірок
check_results         # Результати по сервісах
alerts                # Алерти та нотифікації
```

### Тестування

```bash
# Запуск тестів
pytest tests/

# Тестування з покриттям
pytest --cov=. tests/
```

## 🔐 Безпека

- Всі API ключі зберігаються в змінних оточення
- Сесії захищені CSRF токенами
- Валідація та санітизація всіх входів
- Шифрування чутливих даних в БД

## 📈 Продукційне розгортання

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
```

### Systemd сервіс

```ini
[Unit]
Description=Counterparty Verification System
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/gunicorn --bind unix:/tmp/counterparty.sock app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx конфігурація

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://unix:/tmp/counterparty.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/app/static/;
    }
}
```

## 🤝 Внесок у проект

1. Fork репозиторію
2. Створіть feature branch (`git checkout -b feature/amazing-feature`)
3. Commit зміни (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Створіть Pull Request

## 📄 Ліцензія

Цей проект ліцензовано під MIT License - дивіться файл [LICENSE](LICENSE) для деталей.

## ⚠️ Застереження

Цей додаток призначений для інформаційних цілей та попередньої перевірки. Результати не повинні бути єдиною основою для прийняття бізнес-рішень. Завжди проводьте додаткову due diligence перевірку важливих контрагентів.

## 📞 Підтримка

Якщо у вас виникли питання або проблеми:

1. Перевірте [Issues](../../issues) на GitHub
2. Створіть новий Issue з детальним описом
3. Надішліть Pull Request з виправленнями

---

**Створено з ❤️ для автоматизації перевірки контрагентів**