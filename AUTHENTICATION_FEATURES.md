# Функциональность восстановления пароля и подтверждения email

## Реализованные функции

### 1. **Восстановление пароля (Password Reset)**

#### Маршруты:
- `GET/POST /reset-password-request` - запрос на восстановление пароля
- `GET/POST /reset-password/<token>` - установка нового пароля с токеном

#### Функции:
- `generate_reset_token(user)` - генерирует токен с истечением 24 часа
- `verify_reset_token(token)` - проверяет валидность токена
- `send_password_reset_email(user, token)` - отправляет письмо с ссылкой

#### Форма:
- `PasswordResetRequestForm` - ввод email для восстановления
- `PasswordResetForm` - ввод нового пароля

#### HTML шаблоны:
- `templates/auth/reset_password_request.html` - форма запроса
- `templates/auth/reset_password.html` - форма установки нового пароля

#### Поток:
1. Пользователь вводит email на странице восстановления
2. Система генерирует 24-часовой токен
3. На email отправляется ссылка с токеном
4. Пользователь переходит по ссылке и создает новый пароль
5. Пароль обновляется в БД, токен удаляется

---

### 2. **Подтверждение email (Email Confirmation)**

#### Маршруты:
- `GET /confirm/<token>` - подтверждение email по токену
- `GET /resend-confirmation` - повторная отправка подтверждения

#### Функции:
- `generate_confirmation_token()` - генерирует токен подтверждения (User model)
- `confirm_email(token)` - подтверждает email по токену (User model)
- `send_confirmation_email(user)` - отправляет письмо с подтверждением

#### HTML шаблоны:
- `templates/auth/confirm_email.html` - страница успешного подтверждения
- `templates/auth/resend_confirmation.html` - форма повторной отправки

#### Поток:
1. При регистрации генерируется токен подтверждения
2. На email отправляется ссылка подтверждения
3. Пользователь переходит по ссылке и подтверждает адрес
4. Флаг `is_email_confirmed` устанавливается в True

---

## База данных (Модель User)

```python
# Поля для управления подтверждением email:
email_confirmation_token = db.Column(db.String(100), unique=True)
is_email_confirmed = db.Column(db.Boolean, default=False)

# Поля для восстановления пароля:
password_reset_token = db.Column(db.String(100), unique=True)
password_reset_expires = db.Column(db.DateTime)
```

---

## Конфигурация email (Flask-Mail)

### config.py
```python
MAIL_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('SMTP_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
MAIL_USERNAME = os.environ.get('SMTP_USERNAME')
MAIL_PASSWORD = os.environ.get('SMTP_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@vatverification.com')
```

### application.py
```python
from flask_mail import Mail
mail = Mail()
mail.init_app(app)
```

### notifications/alerts.py
```python
def send_email(subject, recipient, text_body, html_body=None):
    """Отправка email через Flask-Mail"""
    msg = Message(
        subject=subject,
        recipients=[recipient],
        body=text_body,
        html=html_body,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(msg)
```

---

## Переменные окружения (.env на Render)

```
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@your-domain.com
```

---

## Ссылки в UI

### login.html
- Ссылка "Passwort vergessen?" на странице логина ведет на `/reset-password-request`

### register.html
- Объяснение что нужно подтвердить email после регистрации

### Emails
- Письмо о подтверждении: ссылка на `/confirm/<token>`
- Письмо о восстановлении: ссылка на `/reset-password/<token>`

---

## Безопасность

✅ Токены генерируются через `secrets.token_urlsafe(32)`
✅ Пароли хешируются через `werkzeug.security`
✅ Токены восстановления истекают через 24 часа
✅ Email отправляется только для зарегистрированных пользователей
✅ Используется HTTPS для безопасной передачи токенов

---

## Текущий статус

- ✅ Все маршруты реализованы
- ✅ Все формы созданы и валидируются
- ✅ HTML шаблоны оформлены (Bootstrap 5)
- ✅ Email конфигурация готова
- ✅ База данных имеет все необходимые поля
- ✅ Функции отправки email работают
- ✅ Развернуто на Render с автоматическим redeploy

## Использование

### Тестирование локально:

```bash
# 1. Запустить приложение
python application.py

# 2. Перейти на /register и создать аккаунт

# 3. На странице логина нажать "Passwort vergessen?"

# 4. Ввести email и отправить запрос

# 5. В консоли или email увидеть ссылку восстановления

# 6. Перейти по ссылке и установить новый пароль
```

### На продакшене (Render):

Все настроено автоматически через переменные окружения. При регистрации письма отправляются на реальный SMTP сервер.
