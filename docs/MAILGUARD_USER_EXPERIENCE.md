# 🔐 OAuth Flow - Как это работает для пользователя

## Сравнение: Что делает разработчик vs пользователь

```
╔════════════════════════════════════════════════════════════════════╗
║  РАЗРАБОТЧИК (ВЫ) - ОДИН РАЗ                                       ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  1. Google Cloud Console                                           ║
║     ├─ Создать проект "VAT Bot MailGuard"                         ║
║     ├─ Включить Gmail API                                         ║
║     ├─ Создать OAuth 2.0 Client                                   ║
║     └─ Получить: GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET            ║
║                                                                    ║
║  2. Azure Portal                                                   ║
║     ├─ Создать App Registration "VAT Bot MailGuard"               ║
║     ├─ Настроить API Permissions (Mail.ReadWrite, Mail.Send)      ║
║     ├─ Создать Client Secret                                      ║
║     └─ Получить: MS_CLIENT_ID + MS_CLIENT_SECRET + MS_TENANT_ID   ║
║                                                                    ║
║  3. Render.com Environment Variables                               ║
║     ├─ GMAIL_CLIENT_ID=xxx                                         ║
║     ├─ GMAIL_CLIENT_SECRET=xxx                                     ║
║     ├─ MS_CLIENT_ID=xxx                                            ║
║     ├─ MS_CLIENT_SECRET=xxx                                        ║
║     ├─ MS_TENANT_ID=common                                         ║
║     └─ MAILGUARD_ENCRYPTION_KEY=xxx (Fernet key)                   ║
║                                                                    ║
║  4. Deploy кода                                                    ║
║     └─ git push → Render автоматически деплоит                     ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝


╔════════════════════════════════════════════════════════════════════╗
║  ПОЛЬЗОВАТЕЛЬ - ПРОСТОЙ ПРОЦЕСС (30 секунд)                        ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ШАГИ ДЛЯ ПОЛЬЗОВАТЕЛЯ:                                            ║
║                                                                    ║
║  1. Открыть страницу                                               ║
║     https://vat-bot-1.onrender.com/mailguard/accounts              ║
║                                                                    ║
║  2. Нажать кнопку                                                  ║
║     [🔴 Подключить Gmail]  или  [🔵 Подключить Microsoft]          ║
║                                                                    ║
║  3. Увидеть официальный popup Google/Microsoft                     ║
║     ┌────────────────────────────────────────┐                    ║
║     │  Google                          [x]   │                    ║
║     │                                         │                    ║
║     │  VAT Bot MailGuard хочет получить      │                    ║
║     │  доступ к вашему Google Account        │                    ║
║     │                                         │                    ║
║     │  Это позволит приложению:              │                    ║
║     │  ✓ Читать вашу почту                   │                    ║
║     │  ✓ Отправлять письма от вашего имени   │                    ║
║     │                                         │                    ║
║     │  [  Отмена  ]      [ Разрешить ]       │                    ║
║     └────────────────────────────────────────┘                    ║
║                                                                    ║
║  4. Нажать "Разрешить"                                             ║
║                                                                    ║
║  5. ✅ Готово! Почта подключена                                    ║
║                                                                    ║
║  ────────────────────────────────────────────────────────────────  ║
║                                                                    ║
║  ЧТО ПОЛЬЗОВАТЕЛЬ НЕ ВИДИТ:                                        ║
║  ❌ Client ID / Client Secret                                      ║
║  ❌ API консоли (Google Cloud / Azure)                             ║
║  ❌ Переменные окружения                                           ║
║  ❌ Токены доступа (они шифруются автоматически)                   ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 🔄 Технический процесс (что происходит под капотом)

### 1. Пользователь нажимает "Подключить Gmail"

```python
# views.py
@mailguard_bp.route('/auth/gmail')
@login_required
def auth_gmail():
    # Генерируем URL для OAuth (используя ВАШИ ключи из env)
    auth_url = get_gmail_auth_url(user_id=current_user.id)
    # Редиректим пользователя на Google
    return redirect(auth_url)
```

### 2. Google показывает свой официальный popup

```
Пользователь видит:
- Логотип Google
- Название вашего приложения: "VAT Bot MailGuard"
- Запрашиваемые разрешения (scopes)
- Кнопки "Отмена" / "Разрешить"
```

### 3. Пользователь нажимает "Разрешить"

```
Google перенаправляет на ваш callback URL:
https://vat-bot-1.onrender.com/mailguard/auth/gmail/callback?code=4/0AY0e-xxx...
```

### 4. Ваш сервер обменивает код на токены

```python
# views.py
@mailguard_bp.route('/auth/gmail/callback')
@login_required
def auth_gmail_callback():
    code = request.args.get('code')
    
    # Обмениваем код на токены (используя ВАШИ секретные ключи)
    tokens = exchange_gmail_code(code)
    
    # Шифруем токены Fernet ключом
    encrypted_token = encrypt_token(tokens['access_token'])
    encrypted_refresh = encrypt_token(tokens['refresh_token'])
    
    # Сохраняем в БД для этого пользователя
    account = MailAccount(
        user_id=current_user.id,
        provider='gmail',
        email=tokens['email'],
        access_token=encrypted_token,  # Зашифровано!
        refresh_token=encrypted_refresh,  # Зашифровано!
        expires_at=datetime.now() + timedelta(seconds=tokens['expires_in'])
    )
    db.session.add(account)
    db.session.commit()
    
    flash('Gmail успешно подключен!', 'success')
    return redirect(url_for('mailguard.accounts'))
```

### 5. Пользователь видит подключенный аккаунт

```
На странице /mailguard/accounts:

╔═══════════════════════════════════════════════════════════╗
║  Подключенные аккаунты                                    ║
╠═══════════════════════════════════════════════════════════╣
║  🔴 Gmail  |  user@gmail.com  |  ✅ Активен  |  [⚙️ 🔄 🗑️] ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🔒 Безопасность

### Что хранится в базе данных:

```sql
-- Токены ЗАШИФРОВАНЫ Fernet ключом
MailAccount:
  id: 1
  user_id: 42
  provider: 'gmail'
  email: 'user@gmail.com'
  access_token: 'gAAAAABl...'  ← Зашифрованная строка (невозможно прочитать без ключа)
  refresh_token: 'gAAAAABl...' ← Зашифрованная строка
  expires_at: '2025-10-29 15:30:00'
```

### Что НЕ хранится:

- ❌ Пароль пользователя (Google OAuth не передает пароли!)
- ❌ Client Secret (он в env variables на сервере)
- ❌ Незашифрованные токены

### Доступ к токенам:

```python
# Только с MAILGUARD_ENCRYPTION_KEY можно расшифровать
decrypted_token = decrypt_token(account.access_token)

# Без ключа:
print(account.access_token)  
# → 'gAAAAABl9kP3x...' (бесполезная строка)
```

---

## 📝 Итого

**Для пользователя подключение почты = 3 клика:**
1. Кнопка "Подключить Gmail"
2. Popup от Google → "Разрешить"
3. Редирект обратно → "✅ Подключено"

**Пользователь никогда не видит:**
- Ваши Client ID / Secret
- API консоли
- Токены доступа
- Технические детали

**Все как в других сервисах:**
- Trello подключение к Google Drive
- Slack подключение к Gmail
- Notion подключение к Google Calendar

**Это стандартный OAuth 2.0 flow, используемый везде!**
