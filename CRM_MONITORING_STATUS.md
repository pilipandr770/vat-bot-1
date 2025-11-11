# CRM & Monitoring System - Status Report

## Текущее состояние (12 ноября 2025)

### ✅ ЧТО РАБОТАЕТ:

#### 1. **База данных - полностью настроена**
```python
# crm/models.py
✅ Company - данные запрашивающей компании
✅ Counterparty - данные контрагентов для проверки
✅ VerificationCheck - сессии проверки
✅ CheckResult - результаты от каждого сервиса
✅ Alert - алерты об изменениях
```

#### 2. **Сохранение данных при верификации**
```python
# application.py - route /verify
✅ Создаётся/находится Company с user_id
✅ Создаётся/находится Counterparty с user_id
✅ Создаётся VerificationCheck
✅ Сохраняются CheckResult для каждого сервиса
✅ Рассчитывается overall_status и confidence_score
```

#### 3. **CRM интерфейс**
```
✅ Blueprint: crm_bp зарегистрирован
✅ Routes: /crm/, /crm/counterparty/<id>
✅ Templates: templates/crm/index.html, counterparty_details.html
✅ Навигация: Ссылка "CRM" в главном меню
```

#### 4. **Система мониторинга (реализована, но НЕ запущена)**
```python
# crm/monitor.py
✅ MonitoringService с методом run_daily_monitoring()
✅ Поиск активных проверок (is_monitoring_active=True)
✅ Повторная проверка через все сервисы
✅ Обнаружение изменений (_detect_changes)
✅ Создание Alert при изменениях
```

---

### ❌ ЧТО НЕ РАБОТАЕТ:

#### 1. **Пользователь не видит контрагентов в CRM**
**Проблема:** После проверки контрагент не отображается в списке

**Возможные причины:**
- ❓ user_id не сохраняется корректно
- ❓ Проблема с запросом в `/crm/` route
- ❓ Ошибка в шаблоне

**Проверка:**
```sql
-- Проверить, сохраняются ли counterparties с user_id
SELECT id, user_id, company_name, vat_number, created_at 
FROM vat_verification.counterparties 
WHERE user_id IS NOT NULL;

-- Проверить verification_checks
SELECT id, user_id, counterparty_id, overall_status, check_date
FROM vat_verification.verification_checks
ORDER BY check_date DESC LIMIT 10;
```

#### 2. **Ежедневный мониторинг НЕ запущен**
**Проблема:** Нет автоматического scheduler для ежедневной проверки

**Что нужно:**
- Добавить APScheduler job
- Настроить cron-выражение для запуска (например, каждую ночь в 02:00)
- Добавить логирование результатов

**Решение:**
```python
# В application.py или отдельный файл scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from crm.monitor import MonitoringService

scheduler = BackgroundScheduler()

def run_daily_monitoring_job():
    """Фоновая задача для ежедневного мониторинга"""
    monitoring_service = MonitoringService()
    result = monitoring_service.run_daily_monitoring(days_back=30)
    logger.info(f"Daily monitoring completed: {result}")

# Запуск каждый день в 02:00 UTC
scheduler.add_job(
    run_daily_monitoring_job,
    'cron',
    hour=2,
    minute=0,
    id='daily_monitoring',
    replace_existing=True
)

scheduler.start()
```

#### 3. **Email уведомления НЕ отправляются**
**Проблема:** Alert создаются, но пользователь не получает уведомления

**Что нужно:**
- Настроить Flask-Mail или SendGrid
- Создать шаблоны email (HTML + plain text)
- Добавить фоновую отправку через Celery или APScheduler

**Решение:**
```python
# crm/notifications.py (НУЖНО СОЗДАТЬ)
from flask_mail import Mail, Message

def send_alert_notification(alert: Alert, user_email: str):
    """Отправить email уведомление об alert"""
    msg = Message(
        subject=f'🚨 Alert: {alert.alert_type}',
        recipients=[user_email],
        html=render_template('emails/alert_notification.html', alert=alert)
    )
    mail.send(msg)
    
    alert.is_sent = True
    alert.sent_at = datetime.utcnow()
    db.session.commit()
```

#### 4. **is_monitoring_active по умолчанию TRUE**
**Потенциальная проблема:** Все проверки автоматически попадают в мониторинг

**Рекомендация:** Добавить кнопку "Начать мониторинг" в UI для явного включения

---

## 🔧 План исправления

### Шаг 1: Диагностика CRM отображения (СРОЧНО)
```python
# 1. Проверить логи при заходе на /crm/
# 2. Добавить debug логирование в crm/routes.py:

@crm_bp.route('/')
@login_required
def index():
    logger.debug(f"CRM index - User ID: {current_user.id}")
    counterparties = Counterparty.query.filter_by(user_id=current_user.id).all()
    logger.debug(f"Found {len(counterparties)} counterparties for user")
    # ... rest of code
```

### Шаг 2: Добавить APScheduler для мониторинга
```python
# crm/scheduler.py (СОЗДАТЬ НОВЫЙ ФАЙЛ)
from apscheduler.schedulers.background import BackgroundScheduler
from crm.monitor import MonitoringService
import logging

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def setup_monitoring_scheduler(app):
    """Настройка scheduler для ежедневного мониторинга"""
    
    def run_daily_monitoring():
        with app.app_context():
            try:
                monitoring_service = MonitoringService()
                result = monitoring_service.run_daily_monitoring(days_back=30)
                logger.info(f"Daily monitoring completed: {result}")
            except Exception as e:
                logger.error(f"Daily monitoring failed: {e}")
    
    # Запуск каждый день в 02:00 UTC
    scheduler.add_job(
        run_daily_monitoring,
        'cron',
        hour=2,
        minute=0,
        id='daily_monitoring',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Monitoring scheduler started")
    
    return scheduler
```

### Шаг 3: Настроить email уведомления
```python
# config.py - добавить настройки
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = True
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

# crm/notifications.py (СОЗДАТЬ)
from flask_mail import Mail, Message
from flask import render_template

mail = Mail()

def send_alert_email(alert: Alert, user):
    """Отправить email об alert"""
    try:
        msg = Message(
            subject=f'🚨 CRM Alert: {alert.alert_type}',
            recipients=[user.email],
            html=render_template('emails/alert.html', alert=alert, user=user)
        )
        mail.send(msg)
        
        alert.is_sent = True
        alert.sent_at = datetime.utcnow()
        db.session.commit()
        
        return True
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False
```

### Шаг 4: Добавить UI управление мониторингом
```html
<!-- templates/crm/counterparty_details.html -->
<div class="card mb-3">
    <div class="card-header">
        <h5>Мониторинг статуса</h5>
    </div>
    <div class="card-body">
        {% if counterparty.is_monitored %}
            <span class="badge bg-success">Мониторинг активен</span>
            <button class="btn btn-sm btn-warning" onclick="toggleMonitoring({{ counterparty.id }}, false)">
                Отключить мониторинг
            </button>
        {% else %}
            <span class="badge bg-secondary">Мониторинг отключён</span>
            <button class="btn btn-sm btn-success" onclick="toggleMonitoring({{ counterparty.id }}, true)">
                Включить мониторинг
            </button>
        {% endif %}
        
        <small class="text-muted d-block mt-2">
            Автоматическая проверка изменений каждые 24 часа
        </small>
    </div>
</div>
```

---

## 📊 Текущая архитектура

### Процесс верификации:
```
1. User заполняет форму на /verify
   ↓
2. POST /verify → application.py
   ↓
3. get_or_create_company(user_id) → Company
4. get_or_create_counterparty(user_id) → Counterparty
5. create VerificationCheck(user_id)
   ↓
6. run_verification_services() → результаты
   ↓
7. save_verification_results() → CheckResult
8. calculate overall_status → обновление VerificationCheck
   ↓
9. JSON response → frontend
```

### Процесс мониторинга (должен быть):
```
1. APScheduler запускается каждый день в 02:00
   ↓
2. MonitoringService.run_daily_monitoring()
   ↓
3. Найти все is_monitoring_active=True
   ↓
4. Для каждой проверки:
   - Повторно запустить verification services
   - Сравнить с последними результатами
   - Если есть изменения → создать Alert
   ↓
5. Отправить email уведомления для новых Alert
   ↓
6. Логировать summary результатов
```

---

## 🧪 Тестирование

### 1. Проверка сохранения в CRM:
```bash
# 1. Выполнить проверку через /verify
# 2. Проверить БД:
psql -U postgres -d vat_bot_production
\c vat_bot_production
SET search_path TO vat_verification;

SELECT * FROM counterparties WHERE user_id = <YOUR_USER_ID>;
SELECT * FROM verification_checks WHERE user_id = <YOUR_USER_ID>;

# 3. Открыть /crm/ и проверить список
```

### 2. Тестирование мониторинга:
```python
# В Flask shell
flask shell

from crm.monitor import MonitoringService
from crm.models import VerificationCheck

# Найти тестовую проверку
check = VerificationCheck.query.first()
check.is_monitoring_active = True
db.session.commit()

# Запустить мониторинг вручную
monitoring_service = MonitoringService()
result = monitoring_service.run_daily_monitoring(days_back=30)
print(result)
```

### 3. Проверка алертов:
```python
from crm.models import Alert

# Проверить созданные алерты
alerts = Alert.query.all()
for alert in alerts:
    print(f"{alert.severity}: {alert.message} (sent: {alert.is_sent})")
```

---

## 📝 TODO List

### Критические (срочно):
- [ ] **Диагностировать почему контрагенты не видны в CRM**
  - Проверить логи /crm/ route
  - Проверить БД user_id в counterparties
  - Добавить debug логирование
  
- [ ] **Добавить APScheduler для ежедневного мониторинга**
  - Создать crm/scheduler.py
  - Интегрировать в application.py
  - Настроить cron для 02:00 UTC

### Важные (на этой неделе):
- [ ] **Настроить email уведомления**
  - Установить Flask-Mail
  - Создать templates/emails/alert.html
  - Добавить SMTP настройки в .env

- [ ] **Добавить UI управление мониторингом**
  - Кнопка "Включить/Выключить мониторинг"
  - Индикатор статуса мониторинга
  - История изменений

### Улучшения (следующий месяц):
- [ ] Добавить фильтры и поиск в CRM
- [ ] Экспорт данных в CSV/Excel
- [ ] Dashboard с графиками изменений
- [ ] Webhook интеграция для Slack/Telegram
- [ ] Настройка частоты мониторинга (daily/weekly)

---

## 🚀 Быстрый старт для исправления

```bash
# 1. Проверить текущее состояние БД
flask shell
>>> from crm.models import Counterparty, VerificationCheck
>>> Counterparty.query.count()
>>> VerificationCheck.query.count()

# 2. Добавить scheduler (следующий commit)
# Создать crm/scheduler.py и интегрировать

# 3. Тестировать /crm/ route
curl -b cookies.txt http://localhost:5000/crm/

# 4. Проверить логи
tail -f logs/app.log | grep CRM
```

---

**Последнее обновление:** 12 ноября 2025
**Статус:** Система реализована на 80%, но не активирована
**Приоритет:** HIGH - нужно срочно исправить отображение и запустить monitoring
