# TEST MODE CONFIGURATION

## Email Confirmation - DISABLED ⚠️

В тестовом режиме email-подтверждение отключено для упрощения тестирования.

### Изменения в коде:

#### 1. Регистрация (auth/routes.py, функция register)
- ✅ `user.is_email_confirmed = True` - автоматически устанавливается при создании
- ❌ `user.generate_confirmation_token()` - закомментировано
- ❌ `send_confirmation_email(user)` - закомментировано
- 📝 Сообщение изменено на: "Registrierung erfolgreich! Sie können sich jetzt anmelden."

#### 2. Логин (auth/routes.py, функция login)
- ❌ Проверка `if not user.is_email_confirmed:` - закомментирована
- ❌ Отправка повторного email - отключена

#### 3. Admin пользователь
- ✅ В create_admin.py уже установлено `is_email_confirmed=True`

### Для продакшна нужно будет:

1. **Настроить SMTP сервер** в `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@vatverification.com
```

2. **Раскомментировать код** в auth/routes.py:
   - Убрать комментарии с проверок email_confirmed
   - Убрать комментарии с вызовов send_confirmation_email()
   - Раскомментировать user.generate_confirmation_token()

3. **Изменить сообщение** при регистрации обратно на:
   ```python
   flash('Registrierung erfolgreich! Bitte überprüfen Sie Ihre E-Mail, um Ihr Konto zu bestätigen.', 'success')
   ```

### Тестирование

Теперь вы можете:
1. Регистрироваться без email-подтверждения
2. Сразу входить в систему после регистрации
3. Использовать admin аккаунт: admin@example.com / admin123

### Места где помечен TEST MODE:

- `auth/routes.py` - строка 40: `# TEST MODE: Email confirmation disabled`
- `auth/routes.py` - строка 41: `user.is_email_confirmed = True`
- `auth/routes.py` - строка 42: `# user.generate_confirmation_token()  # Disabled for testing`
- `auth/routes.py` - строка 56: `# TEST MODE: Email confirmation disabled`
- `auth/routes.py` - строка 57: `# send_confirmation_email(user)  # Disabled for testing`
- `auth/routes.py` - строка 91: `# TEST MODE: Email confirmation check disabled`
- `auth/routes.py` - строки 92-95: закомментированная проверка email
