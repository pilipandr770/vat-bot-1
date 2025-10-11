# 🚀 VAT Verification Platform - Quick Start (TEST MODE)

## ✅ Email-подтверждение ОТКЛЮЧЕНО

Email-верификация отключена для удобства тестирования. Вы можете регистрироваться и входить в систему **БЕЗ** подтверждения email.

---

## 🎯 Быстрый старт

### Запуск приложения

```bash
python app.py
```

Откроется: **http://localhost:5000**

### Тестовые данные

**Admin аккаунт:**
- Email: `admin@example.com`
- Пароль: `admin123`

**Новый пользователь:**
- Просто зарегистрируйтесь с любым email (даже несуществующим)
- Сразу входите - БЕЗ подтверждения email!

---

## 📖 Документация

| Файл | Описание |
|------|----------|
| **[README_EMAIL_DISABLED.md](README_EMAIL_DISABLED.md)** | 🎯 **НАЧНИТЕ ЗДЕСЬ** - Полная инструкция |
| [TEST_RESULTS_SUCCESS.md](TEST_RESULTS_SUCCESS.md) | ✅ Результаты тестирования |
| [COMPLETE_TEST_MODE_SUMMARY.md](COMPLETE_TEST_MODE_SUMMARY.md) | 📋 Резюме изменений |
| [TEST_MODE_CONFIG.md](TEST_MODE_CONFIG.md) | 🔧 Техническая конфигурация |

---

## 🧪 Тестирование

### 1. Регистрация
```
http://localhost:5000/auth/register
→ Заполните форму
→ Сразу можете войти!
```

### 2. Логин
```
http://localhost:5000/auth/login
→ Email + пароль
→ Доступ к Dashboard
```

### 3. Dashboard
```
http://localhost:5000/dashboard
→ Верификация контрагентов
```

---

## ⚙️ Настройки

### База данных
- **Локально:** SQLite (`instance/counterparty_verification.db`)
- **Продакшн:** PostgreSQL (настроено в `.env`)

### Переключение режимов

**TEST MODE (текущий):**
```env
DATABASE_URL=sqlite:///counterparty_verification.db
```

**PRODUCTION MODE:**
```env
DATABASE_URL=postgresql://...
MAIL_SERVER=smtp.gmail.com
# + раскомментируйте код проверки email в auth/routes.py
```

---

## 🔍 Что изменилось

Все изменения помечены `# TEST MODE` в коде:

**auth/routes.py:**
- Строка 41: `user.is_email_confirmed = True`
- Строка 57: `# send_confirmation_email(user)` (закомментировано)
- Строки 91-95: проверка email закомментирована

**Подробнее:** [COMPLETE_TEST_MODE_SUMMARY.md](COMPLETE_TEST_MODE_SUMMARY.md)

---

## ✅ Текущий статус

- ✅ Email-подтверждение отключено
- ✅ Регистрация работает
- ✅ Логин работает
- ✅ Dashboard доступен
- ✅ Admin создан
- ✅ База данных настроена
- 🚀 **ГОТОВО К ТЕСТИРОВАНИЮ**

---

## 📞 Поддержка

**Вопросы?** Читайте:
1. [README_EMAIL_DISABLED.md](README_EMAIL_DISABLED.md) - главная инструкция
2. [TEST_RESULTS_SUCCESS.md](TEST_RESULTS_SUCCESS.md) - результаты тестов
3. [TEST_MODE_CONFIG.md](TEST_MODE_CONFIG.md) - техническая документация

---

**Версия:** 1.0 (TEST MODE)  
**Дата:** 11 октября 2025  
**Статус:** ✅ Протестировано и работает
