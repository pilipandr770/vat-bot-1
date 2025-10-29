# 📧 MailGuard - Анализ текущей реализации и план развития

## 📊 Текущее состояние (Что уже есть)

### ✅ Реализовано (80% готово):

#### 1. **База данных (Models)**
```
✅ MailAccount - Хранение почтовых аккаунтов (Gmail/Outlook/IMAP)
✅ MailMessage - Входящие письма с метаданными
✅ MailDraft - Черновики ответов от AI
✅ MailRule - Правила обработки (фильтры)
✅ KnownCounterparty - База известных отправителей
✅ ScanReport - Результаты проверки безопасности
```

#### 2. **OAuth Авторизация**
```python
✅ Gmail OAuth 2.0 (get_gmail_auth_url, exchange_gmail_code)
✅ Microsoft OAuth 2.0 (get_ms_auth_url, exchange_ms_code)
✅ Token refresh mechanism (автообновление токенов)
✅ Encryption (Fernet) для безопасного хранения токенов
⚠️ НО: Роуты /auth/gmail и /auth/microsoft НЕ подключены!
```

#### 3. **Email Connectors**
```
✅ Gmail API client (connectors/gmail.py)
✅ Microsoft Graph API client (connectors/microsoft.py)
✅ IMAP client (connectors/imap.py)
✅ SMTP sender (connectors/smtp.py)
```

#### 4. **Processing Pipeline (tasks.py)**
```python
✅ process_incoming_email() - основная функция обработки
✅ normalize_message() - нормализация данных
✅ find_or_create_counterparty() - поиск в CRM
✅ create_reply_draft() - создание черновика AI
✅ poll_imap_accounts() - периодическая проверка IMAP
✅ check_expired_tokens() - обновление токенов
```

#### 5. **Security Scanner Integration**
```python
✅ scanner_client.py - интеграция с File Scanner
✅ scan_message() - проверка письма и вложений
✅ extract_links() - извлечение ссылок
✅ ScanReport model для хранения результатов
```

#### 6. **AI Reply Generation**
```python
✅ nlp_reply.py - генерация ответов через OpenAI
✅ build_reply() - создание текста ответа
✅ get_counterparty_profile() - получение данных из CRM
```

#### 7. **Dashboard UI**
```
✅ /mailguard/ - главная страница со статистикой
✅ /mailguard/accounts - управление аккаунтами
✅ /mailguard/rules - управление правилами
✅ /mailguard/counterparties - база контрагентов
✅ /mailguard/approve/<id> - одобрение черновиков
```

---

## ❌ Что НЕ реализовано (20% осталось):

### 1. **OAuth Routes (критично!)**
```python
❌ /mailguard/auth/gmail - начало авторизации Gmail
❌ /mailguard/auth/gmail/callback - обработка ответа Google
❌ /mailguard/auth/microsoft - начало авторизации Microsoft
❌ /mailguard/auth/microsoft/callback - обработка ответа Microsoft
❌ /mailguard/accounts/add-imap - форма добавления IMAP аккаунта
```

### 2. **Email Fetching**
```python
❌ Webhook handlers для Gmail/Microsoft (push notifications)
❌ Background scheduler не запущен (APScheduler)
❌ Polling IMAP не активирован
```

### 3. **Sending Emails**
```python
❌ send_draft() - отправка одобренных черновиков
❌ Интеграция с Gmail/Microsoft/SMTP для отправки
```

### 4. **CRM Integration**
```python
⚠️ find_or_create_counterparty() создаёт KnownCounterparty
❌ НО: Нет связи с существующим CRM (crm/models.py -> Counterparty)
❌ Нужно синхронизировать KnownCounterparty ↔ Counterparty
```

### 5. **UI Forms**
```python
❌ Форма добавления IMAP аккаунта (host, port, login, password)
❌ Форма создания/редактирования правил (MailRule)
❌ Интерфейс просмотра и редактирования черновиков
```

---

## 🎯 Ваша идея vs Текущая реализация

### ✅ Что УЖЕ соответствует вашей идее:

1. **Проверка отправителя в CRM** ✅
   ```python
   counterparty = find_or_create_counterparty(email)
   # Создаёт нового или находит существующего
   ```

2. **Автоматическая проверка на вредоносы** ✅
   ```python
   scan_result = scan_message(normalized_msg)
   message.risk_score = scan_result['score']
   # Интеграция с File Scanner + VirusTotal
   ```

3. **Черновик от AI ассистента** ✅
   ```python
   draft = create_reply_draft(message, counterparty, message_data, matched_rule)
   # OpenAI GPT-4 генерирует ответ на основе CRM данных
   ```

4. **Одобрение пользователем** ✅
   ```python
   @mailguard_bp.route('/approve/<int:draft_id>', methods=['POST'])
   def approve_and_send(draft_id):
       draft.approved_by_user = True
       # Пользователь может редактировать и отправить
   ```

### ⚠️ Что нужно доработать:

1. **OAuth авторизация** - роуты есть, но не подключены к views.py
2. **Background processing** - код есть, но scheduler не запущен
3. **Отправка email** - логика есть, но не реализована интеграция
4. **CRM sync** - нужна связь KnownCounterparty ↔ Counterparty

---

## 📋 План реализации (Приоритеты)

### **Фаза 1: OAuth & Account Setup (1-2 дня)**

#### Задача 1.1: Подключить Gmail OAuth
```python
# В views.py добавить:

@mailguard_bp.route('/auth/gmail')
@login_required
def gmail_auth():
    """Начать авторизацию Gmail"""
    auth_url = get_gmail_auth_url()
    return redirect(auth_url)

@mailguard_bp.route('/auth/gmail/callback')
@login_required
def gmail_callback():
    """Обработать ответ от Google"""
    code = request.args.get('code')
    if not code:
        flash('Ошибка авторизации Gmail', 'error')
        return redirect(url_for('mailguard.accounts'))
    
    try:
        tokens = exchange_gmail_code(code)
        
        # Получаем email пользователя
        email = get_gmail_user_email(tokens['access_token'])
        
        # Сохраняем аккаунт
        account = MailAccount(
            user_id=current_user.id,
            provider='gmail',
            email=email,
            access_token=encrypt_token(tokens['access_token']),
            refresh_token=encrypt_token(tokens.get('refresh_token')),
            expires_at=datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        )
        db.session.add(account)
        db.session.commit()
        
        flash(f'Gmail аккаунт {email} успешно подключен!', 'success')
        return redirect(url_for('mailguard.accounts'))
        
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
        return redirect(url_for('mailguard.accounts'))
```

#### Задача 1.2: Подключить Microsoft OAuth
```python
# Аналогично Gmail, но с использованием MSAL библиотеки
@mailguard_bp.route('/auth/microsoft')
@mailguard_bp.route('/auth/microsoft/callback')
```

#### Задача 1.3: IMAP Account Setup Form
```python
@mailguard_bp.route('/accounts/add-imap', methods=['GET', 'POST'])
@login_required
def add_imap_account():
    """Добавить IMAP аккаунт"""
    if request.method == 'POST':
        email = request.form.get('email')
        host = request.form.get('host')  # imap.gmail.com
        port = int(request.form.get('port', 993))
        login = request.form.get('login', email)
        password = request.form.get('password')
        
        # Тестируем подключение
        try:
            from .connectors.imap import test_imap_connection
            test_imap_connection(host, port, login, password)
            
            # Сохраняем
            account = MailAccount(
                user_id=current_user.id,
                provider='imap',
                email=email,
                host=host,
                port=port,
                login=login,
                password=encrypt_token(password)
            )
            db.session.add(account)
            db.session.commit()
            
            flash(f'IMAP аккаунт {email} добавлен!', 'success')
            return redirect(url_for('mailguard.accounts'))
            
        except Exception as e:
            flash(f'Ошибка подключения: {str(e)}', 'error')
    
    return render_template('mailguard/add_imap.html')
```

---

### **Фаза 2: Background Email Processing (2-3 дня)**

#### Задача 2.1: Запустить APScheduler
```python
# В application.py или __init__.py:

from app.mailguard.tasks import setup_scheduler

def create_app():
    app = Flask(__name__)
    # ... другие настройки
    
    # Запускаем планировщик задач
    with app.app_context():
        scheduler = setup_scheduler(app)
    
    return app
```

#### Задача 2.2: Gmail/Microsoft Webhooks
```python
# Gmail Push Notifications через Pub/Sub
@mailguard_bp.route('/webhook/gmail', methods=['POST'])
def gmail_webhook():
    """Обработать push notification от Gmail"""
    data = request.get_json()
    
    # Декодируем message
    import base64
    message_data = json.loads(base64.b64decode(data['message']['data']))
    
    # Получаем email address из historyId
    email_address = message_data.get('emailAddress')
    
    # Находим аккаунт
    account = MailAccount.query.filter_by(email=email_address, provider='gmail').first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Запускаем обработку
    from .tasks import process_incoming_email
    from .connectors.gmail import fetch_new_gmail_messages
    
    new_messages = fetch_new_gmail_messages(account)
    for msg in new_messages:
        process_incoming_email(account.id, msg)
    
    return jsonify({'status': 'ok'})
```

#### Задача 2.3: IMAP Polling
```python
# Уже реализовано в tasks.py, просто активировать:
# setup_scheduler() уже запланирует poll_imap_accounts() каждые 5 минут
```

---

### **Фаза 3: CRM Integration (1 день)**

#### Задача 3.1: Связать KnownCounterparty с Counterparty
```python
# В mailguard/models.py добавить:

class KnownCounterparty(db.Model):
    # ... существующие поля ...
    
    # Добавить связь с основным CRM
    crm_counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparties.id'), nullable=True)
    crm_counterparty = db.relationship('Counterparty', backref='mail_profiles')
```

#### Задача 3.2: Обновить find_or_create_counterparty()
```python
def find_or_create_counterparty(email):
    """Найти или создать контрагента с синхронизацией CRM"""
    from crm.models import Counterparty
    from .models import KnownCounterparty
    
    domain = email.split('@')[-1] if '@' in email else ''
    
    # Ищем в MailGuard
    mail_counterparty = KnownCounterparty.query.filter_by(email=email).first()
    
    if not mail_counterparty:
        # Ищем в основном CRM
        crm_counterparty = Counterparty.query.filter_by(email=email).first()
        
        # Создаём запись в MailGuard
        mail_counterparty = KnownCounterparty(
            display_name=crm_counterparty.name if crm_counterparty else email.split('@')[0],
            email=email,
            domain=domain,
            crm_counterparty_id=crm_counterparty.id if crm_counterparty else None
        )
        db.session.add(mail_counterparty)
        db.session.commit()
    
    return mail_counterparty
```

---

### **Фаза 4: Email Sending (1-2 дня)**

#### Задача 4.1: Реализовать send_draft()
```python
# В tasks.py или новый send.py:

def send_draft(draft, account):
    """Отправить одобренный черновик"""
    if account.provider == 'gmail':
        from .connectors.gmail import send_gmail_message
        send_gmail_message(account, draft)
    
    elif account.provider == 'outlook':
        from .connectors.microsoft import send_outlook_message
        send_outlook_message(account, draft)
    
    elif account.provider == 'imap':
        from .connectors.smtp import send_smtp_message
        send_smtp_message(account, draft)
    
    else:
        raise ValueError(f'Unknown provider: {account.provider}')
```

#### Задача 4.2: Реализовать коннекторы отправки
```python
# В connectors/gmail.py:
def send_gmail_message(account, draft):
    """Отправить email через Gmail API"""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import base64
    from email.mime.text import MIMEText
    
    # Расшифровываем токен
    access_token = decrypt_token(account.access_token)
    
    # Создаём credentials
    creds = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=creds)
    
    # Создаём MIME message
    message = MIMEText(draft.body_text or draft.body_html, 'html' if draft.body_html else 'plain')
    message['to'] = draft.to_email
    message['subject'] = draft.subject
    
    # Отправляем
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
```

---

### **Фаза 5: UI Improvements (1-2 дня)**

#### Задача 5.1: Интерфейс редактирования черновиков
```python
@mailguard_bp.route('/draft/<int:draft_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_draft(draft_id):
    """Редактировать черновик перед отправкой"""
    draft = MailDraft.query.get_or_404(draft_id)
    
    # Проверка доступа
    account = MailAccount.query.filter_by(id=draft.account_id, user_id=current_user.id).first()
    if not account:
        abort(403)
    
    if request.method == 'POST':
        draft.body_text = request.form.get('body_text')
        draft.body_html = request.form.get('body_html')
        draft.subject = request.form.get('subject')
        db.session.commit()
        
        flash('Черновик обновлён', 'success')
        return redirect(url_for('mailguard.dashboard'))
    
    return render_template('mailguard/edit_draft.html', draft=draft)
```

#### Задача 5.2: Форма создания правил
```html
<!-- templates/mailguard/create_rule.html -->
<form method="POST" action="{{ url_for('mailguard.create_rule') }}">
    <input name="name" placeholder="Название правила" required>
    <input name="match_from" placeholder="Email отправителя (опционально)">
    <input name="match_domain" placeholder="Домен (example.com или * для всех)">
    <select name="action">
        <option value="draft">Создать черновик</option>
        <option value="auto_reply">Автоответ</option>
        <option value="quarantine">Карантин</option>
        <option value="ignore">Игнорировать</option>
    </select>
    <input type="checkbox" name="requires_human" checked> Требует одобрения
    <input type="number" name="priority" placeholder="Приоритет (0-100)">
    <button type="submit">Создать</button>
</form>
```

---

## 🎯 Ответ на ваш вопрос: "Что должен сделать пользователь с почтой?"

### ✅ **Рекомендуемый вариант (самый лучший):**

**Пользователь вводит свою почту и даёт права доступа через OAuth в интерфейсе**

### Почему это лучший вариант:

1. **Безопасность** 🔒
   - Никаких паролей не хранится в вашей системе
   - Google/Microsoft управляют доступом (можно отозвать в любой момент)
   - Токены зашифрованы (Fernet encryption)

2. **Удобство для пользователя** ✅
   - 1 клик "Подключить Gmail" → OAuth popup → готово
   - Автообновление токенов (refresh tokens)
   - Поддержка нескольких аккаунтов

3. **Надёжность** 📧
   - Gmail/Outlook push notifications (real-time)
   - Нет необходимости в polling (экономия ресурсов)
   - Официальные API (стабильные, документированные)

4. **Гибкость** 🔧
   - Gmail + Microsoft 365 + IMAP (любая почта)
   - Пользователь контролирует доступ
   - Легко добавить/удалить аккаунты

### Как это выглядит для пользователя:

```
1. Пользователь заходит в /mailguard/accounts
2. Видит кнопки:
   [📧 Подключить Gmail]  [📧 Подключить Microsoft 365]  [⚙️ Добавить IMAP]
   
3. Нажимает "Подключить Gmail":
   → Перенаправление на accounts.google.com
   → Пользователь логинится
   → Разрешает доступ: "Читать и отправлять email от вашего имени"
   → Возврат на /mailguard/accounts
   → ✅ "Gmail: user@example.com подключён"
   
4. Всё! Система автоматически:
   - Получает новые письма (push notifications)
   - Проверяет отправителя в CRM
   - Сканирует на вредоносы
   - Генерирует черновик ответа
   - Показывает в dashboard для одобрения
```

---

## 📊 Сравнение вариантов

| Критерий | OAuth (Gmail/Microsoft) | IMAP/SMTP | Email Forwarding |
|----------|------------------------|-----------|------------------|
| **Безопасность** | ✅ Отлично (токены) | ⚠️ Пароли в БД | ⚠️ Пароли приложения |
| **Удобство** | ✅ 1 клик | ⚠️ Ручной ввод | ⚠️ Сложная настройка |
| **Real-time** | ✅ Push notifications | ❌ Polling | ✅ Instant |
| **Отправка** | ✅ Через API | ✅ SMTP | ❌ Нужен SMTP |
| **Multi-account** | ✅ Легко | ✅ Легко | ⚠️ Сложно |
| **Стоимость** | 🆓 Free (квоты) | 🆓 Free | 🆓 Free |

**Вывод:** OAuth - оптимальный вариант для Gmail/Microsoft, IMAP - для других провайдеров.

---

## 🚀 Roadmap (Полный план)

### **Week 1: OAuth & Account Management**
- [ ] День 1-2: Gmail OAuth routes + callback
- [ ] День 2-3: Microsoft OAuth routes + callback
- [ ] День 3-4: IMAP account form + test connection
- [ ] День 4-5: UI для управления аккаунтами
- [ ] День 5: Тестирование авторизации

### **Week 2: Background Processing**
- [ ] День 1-2: Запуск APScheduler
- [ ] День 2-3: Gmail webhook handler
- [ ] День 3-4: Microsoft webhook handler
- [ ] День 4-5: IMAP polling integration
- [ ] День 5: Тестирование получения писем

### **Week 3: CRM Integration & AI**
- [ ] День 1-2: Связь KnownCounterparty ↔ Counterparty
- [ ] День 2-3: Улучшение AI reply generation
- [ ] День 3-4: Интеграция с File Scanner
- [ ] День 4-5: Rule engine тестирование
- [ ] День 5: End-to-end тестирование pipeline

### **Week 4: Email Sending & UI**
- [ ] День 1-2: Gmail/Microsoft send implementation
- [ ] День 2-3: SMTP send implementation
- [ ] День 3-4: Draft editing interface
- [ ] День 4-5: Rule management UI
- [ ] День 5: Final testing & deployment

---

## ✅ Checklist для запуска

### **Необходимые API Keys:**
```env
# Google Cloud Console (https://console.cloud.google.com)
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxx
GMAIL_PROJECT_ID=xxx

# Azure App Registration (https://portal.azure.com)
MS_CLIENT_ID=xxx
MS_CLIENT_SECRET=xxx
MS_TENANT_ID=common

# OpenAI
OPENAI_API_KEY=sk-xxx

# Encryption
MAILGUARD_ENCRYPTION_KEY=<генерировать Fernet.generate_key()>

# File Scanner (опционально, если отдельный сервис)
FILE_SCANNER_URL=http://localhost:5001/scan
```

### **Google Cloud Setup:**
1. Создать проект в Google Cloud Console
2. Включить Gmail API
3. Создать OAuth 2.0 Client ID (Web application)
4. Добавить redirect URI: `https://vat-bot-1.onrender.com/mailguard/auth/gmail/callback`
5. Настроить OAuth consent screen (продакшн режим для публичного доступа)

### **Azure Setup:**
1. Создать App Registration в Azure Portal
2. Добавить Microsoft Graph API permissions:
   - Mail.ReadWrite
   - Mail.Send
3. Добавить redirect URI: `https://vat-bot-1.onrender.com/mailguard/auth/microsoft/callback`

---

## 💡 Рекомендации

### **Сейчас (немедленно):**
1. ✅ Создать OAuth credentials (Google + Azure)
2. ✅ Реализовать OAuth routes (критично!)
3. ✅ Запустить APScheduler для background tasks

### **Потом (через неделю):**
4. ✅ Webhook handlers для real-time processing
5. ✅ CRM integration (связать с основной CRM)
6. ✅ Email sending implementation

### **В будущем (через месяц):**
7. ✅ Advanced rule engine (ML-based routing)
8. ✅ Custom AI training per user
9. ✅ Analytics dashboard

---

## 📝 Итог

**Что у вас УЖЕ есть:** 80% кода, вся архитектура, все модели, коннекторы, AI интеграция

**Что нужно добавить:** 20% - OAuth роуты, запуск scheduler, email sending

**Самый лучший вариант для пользователя:** OAuth авторизация через интерфейс (Gmail + Microsoft 365 + IMAP для остальных)

**Время реализации:** 2-4 недели для полного запуска

**Первый шаг:** Реализовать OAuth роуты и протестировать подключение Gmail аккаунта

---

*Документ составлен: 29 октября 2025*
*Статус: Ready for implementation*
