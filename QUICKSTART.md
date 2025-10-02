# 🚀 Швидкий старт - Counterparty Verification System

## ✅ Система успішно встановлена!

Сервер запущено на: **http://127.0.0.1:5000**

---

## 📋 Доступні сторінки:

### 1. **Головна сторінка** (Основний інтерфейс)
🔗 http://127.0.0.1:5000/

3-колонковий інтерфейс для перевірки контрагентів:
- Ліва колонка: Дані вашої компанії
- Середня колонка: Дані контрагента  
- Права колонка: Результати перевірки

### 2. **Тестова форма** (Для налагодження)
🔗 http://127.0.0.1:5000/test

Проста тестова форма з попередньо заповненими даними для швидкого тестування API.

### 3. **Історія перевірок**
🔗 http://127.0.0.1:5000/history

Перегляд всіх проведених перевірок з можливістю пагінації.

---

## 🧪 Тестування системи:

### Варіант 1: Через веб-інтерфейс
1. Відкрийте: http://127.0.0.1:5000/test
2. Натисніть "Run Verification"
3. Перевірте результати

### Варіант 2: Через тестовий скрипт
```bash
python test_system.py
```

Цей скрипт перевірить:
- ✅ Підключення до БД
- ✅ VIES сервіс
- ✅ Sanctions сервіс
- ✅ Handelsregister сервіс
- ✅ Створення тестових даних

---

## 🔍 Якщо є проблема 400 (Bad Request):

### Діагностика:
1. Відкрийте тестову форму: http://127.0.0.1:5000/test
2. Заповніть форму і натисніть "Run Verification"
3. Перевірте консоль браузера (F12) на помилки
4. Перевірте термінал Flask на логи

### Можливі причини:
- ❌ Відсутні обов'язкові поля (VAT, company name, counterparty name, country)
- ❌ Неправильний формат даних
- ❌ Проблеми з CORS (якщо запит з іншого домену)

### Рішення:
Перевірте, що всі обов'язкові поля заповнені:

**Для компанії:**
- ✔️ VAT номер
- ✔️ Назва компанії
- ✔️ Юридична адреса

**Для контрагента:**
- ✔️ Назва компанії
- ✔️ Країна

---

## 📊 Приклад правильного запиту:

```javascript
const formData = new FormData();

// Company data
formData.append('company_vat', 'DE123456789');
formData.append('company_name', 'Test Company GmbH');
formData.append('company_address', 'Test Street 1, Berlin');
formData.append('company_email', 'test@example.com');
formData.append('company_phone', '+49 30 12345678');

// Counterparty data
formData.append('counterparty_name', 'Sample AG');
formData.append('counterparty_country', 'DE');
formData.append('counterparty_vat', 'DE987654321');
formData.append('counterparty_address', 'Sample Street, Munich');
formData.append('counterparty_email', 'contact@sample.com');
formData.append('counterparty_domain', 'sample.com');

fetch('http://127.0.0.1:5000/verify', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## 🛠️ Корисні команди:

### Перезапуск сервера:
```bash
# Зупинити: CTRL+C
# Запустити знову:
python app.py
```

### Перевірка БД:
```python
python -c "from app import create_app; from crm.models import db, Company; app = create_app(); app.app_context().push(); print(f'Companies: {Company.query.count()}')"
```

### Очистити БД:
```python
python -c "from app import create_app; from crm.models import db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all(); print('Database reset')"
```

### Запуск тестів:
```bash
python test_system.py
```

---

## 📝 Налаштування API ключів:

Відредагуйте файл `.env` для додавання реальних API ключів:

```env
# VIES (безкоштовний, не потребує ключа)
VIES_API_KEY=

# Handelsregister
HANDELSREGISTER_API_KEY=your_key_here

# OpenCorporates
OPENCORPORATES_API_KEY=your_key_here

# Sanctions API
SANCTIONS_API_KEY=your_key_here

# Telegram (для нотифікацій)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email (для нотифікацій)
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

---

## 🎉 Все готово!

Система повністю функціональна і готова до використання.

Для подальшої розробки дивіться:
- `README.md` - Повна документація
- `.github/copilot-instructions.md` - Інструкції для AI агентів
- `test_system.py` - Приклади тестування

---

**Приємної роботи! 🚀**