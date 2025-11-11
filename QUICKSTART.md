# 🚀 Швидкий старт - Counterparty Verification System

## ✅ Локальна розробка з PostgreSQL

Сервер запускається на: **http://127.0.0.1:5000**

---

## � Крок 1: Встановлення залежностей

```bash
# Клонування репозиторію
git clone <repo-url>
cd vat-bot-1

# Віртуальне середовище
python -m venv venv
venv\Scripts\activate  # Windows

# Встановлення пакетів
pip install -r requirements.txt
```

---

## 🐘 Крок 2: Налаштування PostgreSQL

**Важливо**: Проект використовує PostgreSQL (SQLite не підтримується)

```bash
# Перевірте, що PostgreSQL запущено
# Windows: Services → PostgreSQL Server

# Створіть базу даних
psql -U postgres
CREATE DATABASE vat_bot_dev;
\q
```

**Якщо PostgreSQL на нестандартному порту (5433 замість 5432)**:
Оновіть `.env` файл з правильним портом.

---

## ⚙️ Крок 3: Конфігурація (.env файл)

Створіть `.env` у корені проекту:

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# PostgreSQL (перевірте ваш порт!)
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/vat_bot_dev
DB_SCHEMA=vat_verification

# API Keys (опціонально для тестування)
OPENAI_API_KEY=  # Для MailGuard AI-відповідей
GMAIL_CLIENT_ID=  # Gmail OAuth
GMAIL_CLIENT_SECRET=
MS_CLIENT_ID=  # Microsoft OAuth
MS_CLIENT_SECRET=
```

---

## 🗄️ Крок 4: Міграції бази даних

```bash
# Застосувати всі міграції
flask db upgrade

# Має показати 7 міграцій:
# - 361def0cfaed: Initial migration with all models
# - cd954586ac25: Add OSINT tables
# - c8560cadc898: Add user_id to counterparties
# - f9b5e3a7c2d4: Create MailGuard tables
# - a1b2c3d4e5f6: Add attachment_metadata
# - 6d7e8f9a0b1c: Add OSINT indexes
# - 7b1be3569a24: Add reply instructions to MailRule
```

---

## 👤 Крок 5: Створення адміністратора

```bash
python create_admin.py
```

**Отримаєте**:
- Email: `admin@example.com`
- Password: `admin123`
- Plan: Free (5 checks/month)

⚠️ **Змініть пароль після першого входу!**

---

## 🚀 Крок 6: Запуск сервера

```bash
# Режим розробки з автоперезавантаженням
flask run --debug

# Або через Python
python wsgi.py
```

Відкрийте: **http://127.0.0.1:5000**

---

## 📋 Доступні маршруты:

### 🏠 Головні сторінки
- **Landing Page**: http://127.0.0.1:5000/ (маркетингова сторінка)
- **Dashboard**: http://127.0.0.1:5000/dashboard (після логіна)
- **Login**: http://127.0.0.1:5000/auth/login
- **Register**: http://127.0.0.1:5000/auth/register

### ✅ Counterparty Verification
- **Verification Interface**: http://127.0.0.1:5000/verify (3-колонковий інтерфейс)
- **History**: http://127.0.0.1:5000/history (історія перевірок)

### 🔍 OSINT Scanner
- **OSINT Dashboard**: http://127.0.0.1:5000/osint
- **New Scan**: http://127.0.0.1:5000/osint/scan

### 📧 MailGuard
- **MailGuard Dashboard**: http://127.0.0.1:5000/mailguard
- **Account Management**: http://127.0.0.1:5000/mailguard/accounts
- **Rules Management**: http://127.0.0.1:5000/mailguard/rules

### 👥 CRM
- **Counterparties List**: http://127.0.0.1:5000/crm/counterparties
- **Add Counterparty**: http://127.0.0.1:5000/crm/counterparties/new

### 💳 Subscriptions
- **Pricing**: http://127.0.0.1:5000/pricing
- **My Subscription**: http://127.0.0.1:5000/subscription

---

## 🧪 Тестування системи

### Варіант 1: Через веб-інтерфейс
1. Залогіньтеся: http://127.0.0.1:5000/auth/login
   - Email: `admin@example.com`
   - Password: `admin123`
2. Перейдіть на http://127.0.0.1:5000/verify
3. Заповніть форму і натисніть "Verify Counterparty"

### Варіант 2: Тестовий скрипт
```bash
python test_system.py
```

Перевіряє:
- ✅ Підключення до PostgreSQL
- ✅ VIES сервіс
- ✅ Sanctions сервіс
- ✅ Handelsregister сервіс

---

## � Усунення проблем

### Проблема: Connection refused on port 5432
**Причина**: PostgreSQL працює на нестандартному порту 5433

**Рішення**:
```bash
# Оновіть .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/vat_bot_dev
```

### Проблема: Authentication failed for user "postgres"
**Причина**: Пароль PostgreSQL не встановлено

**Рішення**:
```bash
psql -U postgres
ALTER USER postgres WITH PASSWORD 'postgres';
\q
```

### Проблема: ImportError: cannot import name 'Markup' from 'flask'
**Причина**: Flask-WTF 1.1.1 несумісний з Flask 2.3

**Рішення**:
```bash
pip install Flask-WTF==1.2.1 --upgrade
```

---

## 📊 Структура бази даних

**Схема**: `vat_verification` (PostgreSQL schema isolation)

**Таблиці**:
- `users` - Користувачі та аутентифікація
- `subscriptions` - Підписки (Free/Starter/Pro/Enterprise)
- `payments` - Історія платежів (Stripe)
- `companies` - Ваші компанії
- `counterparties` - Контрагенти
- `verification_checks` - Результати перевірок
- `check_results` - Детальні результати по сервісам
- `osint_scans` - OSINT сканування
- `osint_findings` - Результати OSINT
- `mail_account` - Email акаунти для MailGuard
- `mail_message` - Входящі emails
- `mail_rule` - Правила обробки
- `mail_draft` - AI-генерирувані відповіді
- `known_counterparty` - Відомі контакти
- `scan_report` - Результати сканування вкладень

---

## 🎯 Що далі?

### Імплементовані можливості (Free Tier)
✅ VIES VAT validation  
✅ Sanctions checks (EU/OFAC/UK)  
✅ OSINT Scanner (WHOIS, DNS, SSL Labs)  
✅ CRM with monitoring  
✅ MailGuard database models  
✅ Stripe subscriptions  

### Наступна фаза (Paid APIs Integration)
🔄 OAuth flows (Gmail + Microsoft)  
🔄 Email fetching background jobs  
🔄 AI reply approval workflow  
💰 Premium APIs (Creditsafe, Clearbit, Dow Jones)  
💰 Enhanced verification data sources  

---

## 📚 Додаткова документація

- **Development Guide**: `.github/copilot-instructions.md`
- **MailGuard Implementation**: `MAILGUARD_IMPLEMENTATION_PLAN.md`
- **CRM Features**: `CRM_IMPLEMENTATION_SUMMARY.md`
- **OSINT Guide**: `OSINT_GUIDE.md`
- **Deployment**: `RENDER_AUTO_DEPLOY.md`
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## 🛠️ Корисні команди:

### Перезапуск сервера:
```bash
# Зупинити: CTRL+C
# Запустити знову:
python app.py
```

### Перевірка БД:
```python
python -c "from app import create_app; from crm.models import db, Company; app = create_app(); app.app_context().push(); print(f'Companies: {Company.query.count()}')"
```

### Очистити БД:
```python
python -c "from app import create_app; from crm.models import db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all(); print('Database reset')"
```

### Запуск тестів:
```bash
python test_system.py
```

---

## 📝 Налаштування API ключів:

Відредагуйте файл `.env` для додавання реальних API ключів:

```env
# VIES (безкоштовний, не потребує ключа)
VIES_API_KEY=

# Handelsregister
HANDELSREGISTER_API_KEY=your_key_here

# OpenCorporates
OPENCORPORATES_API_KEY=your_key_here

# Sanctions API
SANCTIONS_API_KEY=your_key_here

# Telegram (для нотифікацій)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email (для нотифікацій)
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

---

## 🎉 Все готово!

Система повністю функціональна і готова до використання.

Для подальшої розробки дивіться:
- `README.md` - Повна документація
- `.github/copilot-instructions.md` - Інструкції для AI агентів
- `test_system.py` - Приклади тестування

---

**Приємної роботи! 🚀**