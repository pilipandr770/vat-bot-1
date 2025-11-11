# Counterparty Verification System

Flask веб-додаток для автоматизованої перевірки контрагентів через інтеграцію з офіційними реєстрами та API. Система приймає дані компанії та контрагента, перевіряє їх через різні джерела (VIES, Handelsregister, санкційні списки) і надає комплексну оцінку надійності.

## 🎯 Основні можливості

- **3-колонковий веб-інтерфейс**: Дані компанії → Дані контрагента → Результати перевірки
- **Автоматизовані перевірки**: VIES VAT, Handelsregister, санкційні списки EU/OFAC/UK
- **Збереження результатів**: Повна історія перевірок з можливістю пошуку
- **Моніторинг змін**: Щоденні перевірки з нотифікаціями про зміни
- **Система алертів**: Email та Telegram повідомлення при виявленні проблем

## 🏗️ Архітектура

```
├── app.py                    # Flask application entry point
├── config.py                 # Configuration management  
├── requirements.txt          # Python dependencies
├── templates/                # Jinja2 templates (3-column UI)
├── static/                   # CSS/JS assets
├── services/                 # API integration modules
│   ├── vies.py              # EU VAT validation
│   ├── handelsregister.py   # German business register
│   └── sanctions.py         # EU/OFAC/UK sanctions lists
├── crm/                     # Database and CRM integration
│   ├── models.py            # SQLAlchemy models
│   ├── save_results.py      # Result persistence logic
│   └── monitor.py           # Daily monitoring
└── notifications/           # Alert system
```

## 🚀 Швидкий старт

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

### 2. Налаштування конфігурації

Скопіюйте `.env` файл і налаштуйте свої API ключі:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database (PostgreSQL локально)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vat_bot_dev
DB_SCHEMA=vat_verification

# API Keys (опціонально для тестування)
VIES_API_KEY=
HANDELSREGISTER_API_KEY=
OPENCORPORATES_API_KEY=
SANCTIONS_API_KEY=

# Notifications (опціонально)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_SERVER=
SMTP_USERNAME=
SMTP_PASSWORD=
```

⚠️ Перед запуском створіть локальну базу даних PostgreSQL `vat_bot_dev` і переконайтеся, що служба PostgreSQL запущена (`createdb vat_bot_dev`).

### 3. Ініціалізація бази даних

```bash
# Ініціалізація міграцій
flask db init

# Створення міграції
flask db migrate -m "Initial migration"

# Застосування міграції
flask db upgrade
```

### 4. Запуск додатку

```bash
# Режим розробки
flask run --debug

# Або через Python
python app.py
```

Відкрийте браузер і перейдіть на `http://localhost:5000`

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