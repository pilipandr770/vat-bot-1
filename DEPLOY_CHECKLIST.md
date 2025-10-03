# ✅ Чек-ліст розгортання на Render.com

## 📋 Перед деплоєм

- [x] Всі зміни закомічені в GitHub
- [x] requirements.txt містить gunicorn
- [x] config.py налаштований для PostgreSQL
- [x] render.yaml створений
- [x] Procfile створений
- [x] DEPLOY.md з інструкціями готовий

## 🗄️ Підготовка бази даних (5 хвилин)

1. **Підключитися до PostgreSQL:**
   ```bash
   psql postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db
   ```

2. **Створити схему:**
   ```sql
   CREATE SCHEMA IF NOT EXISTS vat_verification;
   GRANT ALL PRIVILEGES ON SCHEMA vat_verification TO ittoken_db_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vat_verification TO ittoken_db_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA vat_verification TO ittoken_db_user;
   \q
   ```

## 🚀 Створення Web Service (10 хвилин)

### На Render.com Dashboard:

1. **New → Web Service**
2. **Connect Repository:** `pilipandr770/vat-bot-1`
3. **Settings:**
   - Name: `vat-verification-platform`
   - Region: Frankfurt
   - Branch: `main`
   - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

## 🔑 Environment Variables (Критично!)

### Копіюй-вставляй у Render Dashboard → Environment:

```
FLASK_ENV=production
SECRET_KEY=FdFp5ZVRo4vHTLDlaVQWuLeWOjEAjxsDLmpcD3tTpH4
DATABASE_URL=postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db
DB_SCHEMA=vat_verification
```

### Stripe (Тестові ключі):
```
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Email (Gmail):
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@vatverification.com
MAIL_USE_TLS=True
```

## 🔄 Після першого деплою (5 хвилин)

1. **Відкрити Shell в Render:**
   ```bash
   export FLASK_APP=app.py
   flask db upgrade
   python create_admin.py
   ```

2. **Перевірити:**
   - Відкрити `https://vat-verification-platform.onrender.com`
   - Увійти як admin@example.com / admin123
   - Перевірити Dashboard

## 🎯 Stripe Webhook

1. **Stripe Dashboard → Developers → Webhooks**
2. **Add endpoint:**
   - URL: `https://vat-verification-platform.onrender.com/payments/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.*`
3. **Копіювати Webhook Secret → Render Environment Variables**

## ⏱️ Загальний час: ~20 хвилин

## 🆘 Якщо щось не працює:

1. **Перевірити логи:** Render Dashboard → Service → Logs
2. **Перевірити змінні:** Environment Variables правильно введені?
3. **Перевірити базу:**
   ```bash
   psql $DATABASE_URL
   SET search_path TO vat_verification;
   \dt
   ```
4. **Перезапустити сервіс:** Manual Deploy → Clear build cache & deploy

## 🎉 Готово!

Ваш додаток буде доступний на:
`https://vat-verification-platform.onrender.com`

**Важливо:** Free tier засинає після 15 хвилин неактивності. Перший запит після сну займе ~30 секунд.
