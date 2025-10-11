# 🚀 БЫСТРЫЙ ДЕПЛОЙ НА RENDER

## ⚡ ТРИ КОМАНДЫ - И ГОТОВО!

```bash
# 1. Добавить изменения
git add .

# 2. Коммит
git commit -m "feat: disable email confirmation for testing"

# 3. Деплой (автоматический)
git push origin main
```

⏱️ **Render задеплоит автоматически за 3-4 минуты!**

---

## ✅ Что происходит автоматически:

| Шаг | Что делает Render | Время |
|-----|-------------------|-------|
| 1 | Получает push от GitHub | 1-2 сек |
| 2 | Устанавливает зависимости | 2-3 мин |
| 3 | Собирает приложение | 30 сек |
| 4 | Запускает с новым кодом | 10 сек |
| **ИТОГО** | **Приложение работает!** | **~4 мин** |

---

## 🌐 После деплоя:

**Проверьте:**
- 🌐 https://vat-verification-platform.onrender.com
- 📊 https://dashboard.render.com (статус "Live")

**Протестируйте:**
- Регистрация БЕЗ email → ✅
- Логин БЕЗ проверки email → ✅
- Admin: admin@example.com / admin123 → ✅

---

## 🔧 Если нужно обновить старых пользователей:

```bash
# Подключиться к PostgreSQL
psql postgresql://ittoken_db_user:Xm98VVSZv7cMJkopkdWRkgvZzC7Aly42@dpg-d0visga4d50c73ekmu4g-a/ittoken_db

# Обновить
SET search_path TO vat_verification;
UPDATE users SET is_email_confirmed = true;
\q
```

---

## 📖 Подробная документация:

- **[RENDER_AUTO_DEPLOY.md](RENDER_AUTO_DEPLOY.md)** - полная инструкция
- **[DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** - чеклист деплоя
- **[START_HERE.md](START_HERE.md)** - быстрый старт

---

**Готово! Просто сделайте `git push` 🚀**
