# 🚀 Автоматический деплой на Render.com

## ⚡ Что произойдет автоматически после git push?

### ✅ ДА, деплой пройдет автоматически!

Render.com настроен на автоматическое развертывание при push в ветку `main`.

---

## 📋 Что произойдет шаг за шагом:

### 1. Git Push (вы делаете)
```bash
git add .
git commit -m "feat: disable email confirmation for testing"
git push
```
⏱️ **Время:** ~5 секунд

### 2. Render обнаружит изменения ✅ АВТОМАТИЧЕСКИ
- Render получит webhook от GitHub
- Начнется автоматическая сборка (build)
- Статус можно посмотреть в Dashboard → Deploys

⏱️ **Время:** ~1-2 секунды

### 3. Build Process ✅ АВТОМАТИЧЕСКИ
```bash
# Render выполнит (из render.yaml):
pip install --upgrade pip
pip install -r requirements.txt
```
⏱️ **Время:** ~2-3 минуты

### 4. Deploy ✅ АВТОМАТИЧЕСКИ
```bash
# Render запустит (из render.yaml):
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```
⏱️ **Время:** ~30 секунд

### 5. Приложение запущено ✅ АВТОМАТИЧЕСКИ
🌐 **URL:** https://vat-verification-platform.onrender.com

⏱️ **ИТОГО:** ~3-4 минуты от push до работающего приложения

---

## 🔍 Что НЕ произойдет автоматически:

### ⚠️ База данных НЕ обновится автоматически

**Проблема:**
- На Render используется PostgreSQL
- Новые пользователи там могут иметь `is_email_confirmed = False`

**Решение (если нужно):**

#### Вариант A: Оставить как есть (РЕКОМЕНДУЕТСЯ)
Ничего не делать. Новые пользователи на Render будут регистрироваться с `is_email_confirmed = True` автоматически (благодаря нашим изменениям).

#### Вариант B: Обновить существующих пользователей
Если на Render уже есть пользователи без подтверждения email:

1. **Подключиться к PostgreSQL на Render:**
   ```bash
   psql postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db
   ```

2. **Обновить пользователей:**
   ```sql
   SET search_path TO vat_verification;
   UPDATE users SET is_email_confirmed = true WHERE is_email_confirmed = false;
   SELECT email, is_email_confirmed FROM users;
   \q
   ```

⏱️ **Время:** ~2 минуты (только если нужно)

---

## 📊 Чеклист после деплоя:

### Сразу после push (автоматически):
- [ ] GitHub получил push
- [ ] Render начал build
- [ ] Зависимости установлены
- [ ] Приложение запущено

### Проверка вручную (~2 минуты):
1. **Откройте Render Dashboard:**
   - https://dashboard.render.com
   - Найдите "vat-verification-platform"
   - Проверьте статус: должен быть "Live" (зеленый)

2. **Откройте приложение:**
   - https://vat-verification-platform.onrender.com
   - Должна загрузиться главная страница

3. **Проверьте регистрацию:**
   - Попробуйте зарегистрироваться
   - Должно работать БЕЗ подтверждения email

4. **Проверьте логин:**
   - Admin: admin@example.com / admin123
   - Или новый пользователь
   - Должны войти БЕЗ проверки email

---

## 🔧 Переменные окружения

### ✅ Уже настроены на Render:
- `DATABASE_URL` - PostgreSQL
- `DB_SCHEMA` - vat_verification
- `SECRET_KEY` - генерируется автоматически
- `FLASK_ENV` - production
- `STRIPE_PUBLIC_KEY` - ваш ключ
- `STRIPE_SECRET_KEY` - ваш ключ

### ⏸️ Не настроены (пока не нужны):
- `SMTP_SERVER` - для email (отключен в TEST MODE)
- `SMTP_USERNAME` - для email (отключен в TEST MODE)
- `SMTP_PASSWORD` - для email (отключен в TEST MODE)
- `MAIL_DEFAULT_SENDER` - для email (отключен в TEST MODE)

---

## 🎯 Команды для деплоя:

### Простой деплой (с тестовым режимом):
```bash
# 1. Добавить изменения
git add .

# 2. Коммит с описанием
git commit -m "feat: disable email confirmation for testing"

# 3. Push в main (автоматический деплой)
git push origin main
```

### Если хотите проверить локально перед деплоем:
```bash
# 1. Локальное тестирование
python app.py
# Откройте: http://localhost:5000

# 2. Убедитесь что все работает

# 3. Затем деплой
git add .
git commit -m "feat: disable email confirmation for testing"
git push origin main
```

---

## 📈 Мониторинг деплоя:

### В реальном времени:
1. **Render Dashboard:**
   - https://dashboard.render.com
   - Выберите "vat-verification-platform"
   - Вкладка "Deploys"
   - Смотрите логи в реальном времени

2. **Логи сборки:**
   ```
   Building...
   --> Installing dependencies
   --> Collecting Flask==2.3.3
   --> Collecting SQLAlchemy==2.0.35
   ...
   --> Build successful!
   ```

3. **Логи запуска:**
   ```
   Starting...
   --> Running: gunicorn app:app
   --> [INFO] Starting gunicorn 21.2.0
   --> [INFO] Listening at: http://0.0.0.0:10000
   --> Service live!
   ```

---

## ⚠️ Возможные проблемы:

### Проблема 1: Build Failed
**Причина:** Ошибка в requirements.txt или коде  
**Решение:** Проверьте логи в Render Dashboard

### Проблема 2: Service не запускается
**Причина:** Ошибка в app.py или конфигурации  
**Решение:** Проверьте, что `app = create_app()` есть в app.py

### Проблема 3: База данных не работает
**Причина:** Схема vat_verification не создана  
**Решение:** Выполните SQL команды из DEPLOY_CHECKLIST.md

### Проблема 4: Пользователи не могут войти
**Причина:** Старые пользователи с is_email_confirmed=False  
**Решение:** Обновите их в PostgreSQL (см. Вариант B выше)

---

## 🎉 Итог:

### ДА, после `git push` все пройдет автоматически!

**Вам нужно:**
1. ✅ Сделать `git push origin main`
2. ✅ Подождать 3-4 минуты
3. ✅ Проверить что приложение работает

**Render сделает автоматически:**
1. ✅ Получит изменения из GitHub
2. ✅ Установит зависимости
3. ✅ Соберет приложение
4. ✅ Запустит с новым кодом
5. ✅ Обновит URL

**НЕ нужно:**
- ❌ Заходить в Render Dashboard (если все ОК)
- ❌ Нажимать кнопки вручную
- ❌ Перезапускать сервис
- ❌ Настраивать SMTP (тестовый режим)

---

## 📞 Быстрая справка:

**Сделать деплой:**
```bash
git add .
git commit -m "feat: disable email confirmation for testing"
git push
```

**Проверить статус:**
- Dashboard: https://dashboard.render.com
- Приложение: https://vat-verification-platform.onrender.com

**Обновить существующих пользователей (если нужно):**
```sql
-- Подключиться к PostgreSQL
psql postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db

-- Обновить
SET search_path TO vat_verification;
UPDATE users SET is_email_confirmed = true;
\q
```

---

**Готово к деплою! 🚀**

⏱️ **Ожидаемое время деплоя:** 3-4 минуты  
✅ **Автоматизация:** 100%  
🎯 **Действий вручную:** 0 (после push)
