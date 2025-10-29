# 🚀 Quick Start: OAuth Setup для MailGuard

## Что делать (для разработчика)

### 1️⃣ Получить Google OAuth ключи (5 минут)

1. Перейти: https://console.cloud.google.com
2. Создать проект "VAT Bot MailGuard"
3. Включить Gmail API
4. Создать OAuth 2.0 Client ID:
   - Type: Web application
   - Name: "VAT Bot MailGuard Production"
   - Authorized redirect URIs:
     ```
     https://vat-bot-1.onrender.com/mailguard/auth/gmail/callback
     ```
5. Скопировать:
   - **Client ID** → GMAIL_CLIENT_ID
   - **Client Secret** → GMAIL_CLIENT_SECRET

---

### 2️⃣ Получить Microsoft OAuth ключи (5 минут)

1. Перейти: https://portal.azure.com
2. Azure Active Directory → App registrations → New registration
3. Настройки:
   - Name: "VAT Bot MailGuard"
   - Redirect URI (Web): 
     ```
     https://vat-bot-1.onrender.com/mailguard/auth/microsoft/callback
     ```
4. API Permissions → Add permission → Microsoft Graph:
   - ✅ Mail.ReadWrite
   - ✅ Mail.Send
   - ✅ User.Read
5. Certificates & secrets → New client secret → Copy value
6. Скопировать:
   - **Application (client) ID** → MS_CLIENT_ID
   - **Client secret value** → MS_CLIENT_SECRET
   - **Directory (tenant) ID** → MS_TENANT_ID (или использовать "common")

---

### 3️⃣ Сгенерировать Fernet ключ шифрования

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Скопировать результат → **MAILGUARD_ENCRYPTION_KEY**

---

### 4️⃣ Добавить в Render.com Environment Variables

Перейти: https://dashboard.render.com/web/srv-xxx/env

Добавить 6 переменных:

```
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-xxx
MS_CLIENT_ID=xxx
MS_CLIENT_SECRET=xxx
MS_TENANT_ID=common
MAILGUARD_ENCRYPTION_KEY=xxx
```

**Сохранить → Render автоматически перезапустит сервер**

---

## ✅ Готово!

Теперь пользователи могут:

1. Зайти на https://vat-bot-1.onrender.com/mailguard/accounts
2. Нажать "Подключить Gmail" или "Подключить Microsoft"
3. Разрешить доступ в popup
4. Готово — почта подключена!

---

## 🔍 Проверка работы

### Тест Gmail OAuth:

1. Открыть: https://vat-bot-1.onrender.com/mailguard/auth/gmail
2. Должен открыться Google OAuth popup
3. После "Разрешить" → редирект на /mailguard/accounts
4. Аккаунт должен появиться в списке

### Тест Microsoft OAuth:

1. Открыть: https://vat-bot-1.onrender.com/mailguard/auth/microsoft
2. Должен открыться Microsoft OAuth popup
3. После "Разрешить" → редирект на /mailguard/accounts
4. Аккаунт должен появиться в списке

---

## ⚠️ Troubleshooting

### Ошибка "redirect_uri_mismatch":
- Проверить, что в Google Cloud Console добавлен точный URL:
  ```
  https://vat-bot-1.onrender.com/mailguard/auth/gmail/callback
  ```
- Не должно быть trailing slash в конце!

### Ошибка "invalid_client" (Microsoft):
- Проверить, что MS_CLIENT_SECRET не истек (они expires через 3-24 месяца)
- Проверить, что redirect URI в Azure Portal совпадает с кодом

### Ошибка "encryption key not found":
- Проверить, что MAILGUARD_ENCRYPTION_KEY добавлен в Render env vars
- Проверить, что сервер перезапустился после добавления

---

## 📝 Next Steps

После добавления OAuth credentials:

1. **Phase 1**: Implement OAuth routes (1-2 days)
   - Код уже готов в `oauth.py`
   - Нужно только подключить routes в `views.py`

2. **Phase 2**: Activate email polling (2-3 days)
   - APScheduler уже настроен
   - Нужно только раскомментировать `setup_scheduler(app)` в `application.py`

3. **Phase 3**: Implement sending (1-2 days)
   - SMTP/Gmail API код готов
   - Нужно подключить к `approve_and_send()` route

4. **Phase 4**: Test full workflow
   - Send test email → AI generates reply → approve → send

---

**Total time: 2 weeks for full MailGuard deployment** ✨
