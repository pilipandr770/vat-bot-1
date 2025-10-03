# 🚀 Інструкція з розгортання на Render.com

## Передумови
- Акаунт на [Render.com](https://render.com)
- Проект push в GitHub репозиторій
- Існуюча PostgreSQL база даних на Render

## 📋 Покрокова інструкція

### Крок 1: Підготовка бази даних

Ваша PostgreSQL база: `postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db`

1. **Підключіться до бази через Render Dashboard або psql:**
   ```bash
   psql postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db
   ```

2. **Створіть окрему схему для проекту:**
   ```sql
   CREATE SCHEMA IF NOT EXISTS vat_verification;
   GRANT ALL PRIVILEGES ON SCHEMA vat_verification TO ittoken_db_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vat_verification TO ittoken_db_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA vat_verification TO ittoken_db_user;
   ```

3. **Перевірте створення:**
   ```sql
   SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'vat_verification';
   ```

### Крок 2: Створення Web Service на Render

1. **Перейдіть на Render Dashboard** → New → Web Service

2. **Підключіть GitHub репозиторій:** `pilipandr770/vat-bot-1`

3. **Налаштуйте Build Settings:**
   - **Name:** `vat-verification-platform`
   - **Region:** Frankfurt (або найближчий)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** 
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command:** 
     ```bash
     gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
     ```

### Крок 3: Налаштування Environment Variables

У розділі **Environment** додайте змінні:

#### Обов'язкові:
```
FLASK_ENV=production
SECRET_KEY=<generate-random-32-char-string>
DATABASE_URL=postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db
DB_SCHEMA=vat_verification
```

#### Stripe (отримайте на dashboard.stripe.com):
```
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

#### Email (Gmail або SendGrid):
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@vatverification.com
MAIL_USE_TLS=True
```

#### API Keys (опціонально):
```
VIES_API_KEY=your-key
HANDELSREGISTER_API_KEY=your-key
OPENCORPORATES_API_KEY=your-key
SANCTIONS_API_KEY=your-key
```

### Крок 4: Запуск міграцій

Після першого деплою:

1. **Відкрийте Shell в Render Dashboard:** Your Service → Shell

2. **Запустіть міграції:**
   ```bash
   export FLASK_APP=app.py
   flask db upgrade
   ```

3. **Створіть admin користувача:**
   ```bash
   python create_admin.py
   ```
   (Або створіть через Flask shell)

### Крок 5: Налаштування Stripe Webhook

1. **Отримайте URL вашого додатку:** `https://vat-verification-platform.onrender.com`

2. **Налаштуйте webhook в Stripe Dashboard:**
   - URL: `https://vat-verification-platform.onrender.com/payments/webhook`
   - Події: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`

3. **Скопіюйте Webhook Secret** і додайте в Environment Variables як `STRIPE_WEBHOOK_SECRET`

### Крок 6: Перевірка

1. **Відкрийте додаток:** `https://vat-verification-platform.onrender.com`
2. **Увійдіть як admin:** admin@example.com / admin123
3. **Перевірте Dashboard**
4. **Протестуйте реєстрацію нового користувача**

## 🔧 Налагодження

### Перегляд логів:
```bash
# В Render Dashboard → Logs
```

### Підключення до бази:
```bash
psql $DATABASE_URL
\c ittoken_db
SET search_path TO vat_verification;
\dt  # Показати таблиці
```

### Перезапуск міграцій:
```bash
# В Shell на Render
flask db downgrade
flask db upgrade
```

## 📊 Моніторинг

- **Logs:** Render Dashboard → Service → Logs
- **Metrics:** Render Dashboard → Service → Metrics
- **Database:** Render Dashboard → PostgreSQL → Metrics

## 🔒 Безпека

✅ Змінюйте `SECRET_KEY` перед деплоєм  
✅ Використовуйте Stripe live keys для production  
✅ Налаштуйте CORS якщо потрібно  
✅ Увімкніть HTTPS (автоматично на Render)  

## 💰 Вартість

- **Free Tier:** 
  - Web Service: 750 годин/місяць (достатньо для одного сервісу 24/7)
  - PostgreSQL: 90 днів безкоштовно, потім $7/місяць
  
- **Рекомендація:** Почніть з Free, перейдіть на Starter ($7/місяць) при зростанні трафіку

## 📞 Підтримка

Якщо виникають проблеми:
1. Перевірте логи в Render Dashboard
2. Перевірте Environment Variables
3. Перевірте підключення до бази даних
4. Перевірте міграції: `flask db current`
